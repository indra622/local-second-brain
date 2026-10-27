"""Descriptor-relative bundle access and exclusive local writes."""

import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


class WikiError(Exception):
    pass


def read_input(path):
    path = Path(path)
    with Store(path.parent) as store:
        return store.read(path.name)


def identifier(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise WikiError("ID must be 1-64 lowercase ASCII letters, digits or hyphens")
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        return self

    def __exit__(self, *args):
        os.close(self.fd)

    @contextmanager
    def parent(self, relative, create=False):
        path = PurePosixPath(relative)
        if path.is_absolute() or not path.parts or any(p in ("..", ".") for p in path.parts):
            raise WikiError(f"Unsafe bundle path: {relative}")
        fd = os.dup(self.fd)
        try:
            for part in path.parts[:-1]:
                if create:
                    try:
                        os.mkdir(part, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, path.name
        finally:
            os.close(fd)

    def read(self, relative):
        with self.parent(relative) as (fd, name):
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise WikiError(f"Not a regular file: {relative}")
                return stream.read()

    def create(self, relative, data):
        with self.parent(relative, create=True) as (fd, name):
            handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=fd)
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())

    @contextmanager
    def lock(self):
        try:
            self.create(".lkw.lock", b"active local CLI write\n")
        except FileExistsError as exc:
            raise WikiError("Bundle is locked; after a crash, inspect before removing .lkw.lock") from exc
        try:
            yield
        finally:
            os.unlink(".lkw.lock", dir_fd=self.fd)

    def replace_index(self, before, after):
        if self.read("index.md") != before:
            raise WikiError("index.md changed during this operation")
        self.create(".lkw-index.tmp", after)
        try:
            if self.read("index.md") != before:
                raise WikiError("index.md changed during this operation")
            os.replace(".lkw-index.tmp", "index.md", src_dir_fd=self.fd, dst_dir_fd=self.fd)
        finally:
            try:
                os.unlink(".lkw-index.tmp", dir_fd=self.fd)
            except FileNotFoundError:
                pass

    def files(self):
        def walk(fd, prefix=""):
            for name in sorted(os.listdir(fd)):
                if name in (".obsidian", ".git"):
                    continue
                path = prefix + name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    raise WikiError(f"Symlinks are not supported in bundles: {path}")
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        yield from walk(child, path + "/")
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    yield path
                else:
                    raise WikiError(f"Not a regular file: {path}")
        return list(walk(self.fd))


START = "<!-- lkw:current:start -->\n"
END = "<!-- lkw:current:end -->"


def current_index(text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise WikiError("index.md must contain one intact lkw current block")
    start = text.index(START) + len(START)
    end = text.index(END)
    if end < start:
        raise WikiError("Managed current block markers are reversed")
    entries = {}
    for line in text[start:end].splitlines():
        match = re.fullmatch(r"- \[([a-z0-9][a-z0-9-]{0,63})\]\((concepts/\1/r[0-9]{6}\.md)\)", line)
        if not match or match[1] in entries:
            raise WikiError("Managed current block was edited; refusing to replace it")
        entries[match[1]] = match[2]
    if text[start:end] != render_entries(entries):
        raise WikiError("Managed current block was edited; refusing to replace it")
    return entries, start, end


def render_entries(entries):
    return "".join(f"- [{key}]({entries[key]})\n" for key in sorted(entries))


def init(root):
    path = Path(root)
    if not path.exists():
        path.mkdir(parents=True)
    with Store(path) as store, store.lock():
        if set(os.listdir(store.fd)) != {".lkw.lock"}:
            raise WikiError("init requires an empty target directory")
        store.create("index.md", ("---\nokf_version: '0.2'\n---\n\n# Local knowledge\n\n"
                                  + START + END + "\n").encode())


def capture(root, source, source_id, actor, resource, at):
    identifier(source_id)
    # Explicit input files may live outside the bundle; no decoding or newline conversion.
    data = read_input(source)
    metadata = {"id": source_id, "original_name": Path(source).name,
                "resource": resource, "captured": {"by": actor, "at": at},
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    folder = f"sources/{source_id}"
    with Store(root) as store, store.lock():
        current_index(store.read("index.md").decode("utf-8"))
        # Reserve the whole source directory before either file is written.
        with store.parent(folder, create=True) as (fd, name):
            os.mkdir(name, dir_fd=fd)
        store.create(folder + "/content.raw", data)
        store.create(folder + "/provenance.json", (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode())
    return folder + "/content.raw"
