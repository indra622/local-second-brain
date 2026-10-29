"""Descriptor-relative bundle access and exclusive local writes."""

import errno
import hashlib
import json
import os
import re
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


from .errors import WikiError


LOCK_MARKER = b"lkw:flock:v1\n"
STAGE_PATTERN = re.compile(r"\.lkw-index\.[0-9a-f]{32}\.tmp")


class LockCapabilityError(WikiError):
    pass


def flock(handle, shared=False):
    try:
        import fcntl
    except ImportError as exc:
        raise LockCapabilityError("Native flock is unavailable; writes require supported local macOS/Linux locking", "recovery_required") from exc
    try:
        fcntl.flock(handle, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno in (errno.EAGAIN, errno.EACCES):
            raise WikiError("Bundle writer lock is busy; wait for the active holder", "locked") from exc
        raise


def write_all(handle, data):
    view = memoryview(data)
    while view:
        written = os.write(handle, view)
        if written <= 0:
            raise OSError("Short write made no progress")
        view = view[written:]


def same_inode(left, right):
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def read_input(path):
    path = Path(path)
    with Store(path.parent) as store:
        return store.read(path.name)


def identifier(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise WikiError("ID must be 1-64 lowercase ASCII letters, digits or hyphens")
    return value


def single_line(value, field):
    if not isinstance(value, str) or any(c in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029" for c in value):
        raise WikiError(f"{field} must be a single-line string")


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
            raise WikiError(f"Unsafe bundle path: {relative}", "unsafe_path")
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

    def read(self, relative, max_bytes=None):
        with self.parent(relative) as (fd, name):
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise WikiError(f"Not a regular file: {relative}", "unsafe_path")
                if max_bytes is None:
                    return stream.read()
                if os.fstat(stream.fileno()).st_size > max_bytes:
                    raise WikiError("Inspection file size limit exceeded")
                data = stream.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise WikiError("Inspection file size limit exceeded")
                return data

    def create(self, relative, data):
        with self.parent(relative, create=True) as (fd, name):
            handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=fd)
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())

    def open_lock(self, flags):
        try:
            return os.open(".lkw.lock", flags, 0o644, dir_fd=self.fd)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.EISDIR, errno.ENOTDIR):
                raise WikiError("Unsafe .lkw.lock path", "unsafe_path") from exc
            raise

    def validate_lock(self, handle, marker=True):
        opened = os.fstat(handle)
        try:
            named = os.stat(".lkw.lock", dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise WikiError(".lkw.lock pathname disappeared", "unsafe_path") from exc
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or not stat.S_ISREG(named.st_mode) or named.st_nlink != 1
                or not same_inode(opened, named)):
            raise WikiError("Unsafe or substituted .lkw.lock inode", "unsafe_path")
        if marker and os.pread(handle, len(LOCK_MARKER) + 1, 0) != LOCK_MARKER:
            raise WikiError("Legacy, empty or unknown .lkw.lock; stop writers and inspect; no automatic conversion", "recovery_required")

    @contextmanager
    def lock(self, *, shared=False, create=True):
        flags = (os.O_RDONLY if shared else os.O_RDWR) | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        created = False
        try:
            handle = self.open_lock(flags)
        except FileNotFoundError:
            if shared or not create:
                raise
            try:
                handle = self.open_lock(flags | os.O_CREAT | os.O_EXCL)
                created = True
            except FileExistsError:
                handle = self.open_lock(flags)
        try:
            os.set_inheritable(handle, False)
            self.validate_lock(handle, marker=not created)
            flock(handle, shared)
            self.validate_lock(handle, marker=not created)
            if created:
                write_all(handle, LOCK_MARKER)
                os.fsync(handle)
                os.fsync(self.fd)
                self.validate_lock(handle)
            yield handle
        finally:
            # Never unlink: another inode would form an independent lock domain.
            os.close(handle)

    @contextmanager
    def stage_index(self, data):
        handle = None
        for _ in range(10):
            name = f".lkw-index.{secrets.token_hex(16)}.tmp"
            try:
                handle = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                 0o644, dir_fd=self.fd)
                break
            except FileExistsError:
                continue
        if handle is None:
            raise WikiError("Index staging name collision limit reached; inspect existing artifacts", "already_exists")
        owned = None
        try:
            owned = os.fstat(handle)
            write_all(handle, data)
            os.fsync(handle)
            self._index_stage = (name, handle, owned)
            yield name
        finally:
            self._index_stage = None
            try:
                named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                if owned is not None and stat.S_ISREG(named.st_mode) and named.st_nlink == 1 and same_inode(owned, named):
                    os.unlink(name, dir_fd=self.fd)
            except FileNotFoundError:
                pass
            finally:
                os.close(handle)

    def replace_index(self, before, after):
        stage = getattr(self, '_index_stage', None)
        if stage is None:
            with self.stage_index(after):
                return self.replace_index(before, after)
        name, handle, owned = stage
        if self.read("index.md") != before:
            raise WikiError("index.md changed during this operation", "concurrent_change")
        named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        if (not stat.S_ISREG(named.st_mode) or named.st_nlink != 1 or not same_inode(owned, named)
                or not same_inode(owned, os.fstat(handle)) or os.fstat(handle).st_size != len(after)
                or os.pread(handle, len(after) + 1, 0) != after):
            raise WikiError("Index staging identity or bytes changed", "concurrent_change")
        if self.read("index.md") != before:
            raise WikiError("index.md changed during this operation", "concurrent_change")
        os.replace(name, "index.md", src_dir_fd=self.fd, dst_dir_fd=self.fd)
        os.fsync(self.fd)

    def files(self):
        def walk(fd, prefix=""):
            for name in sorted(os.listdir(fd)):
                if name in (".obsidian", ".git") or (not prefix and name == ".lkw-requests"):
                    continue
                path = prefix + name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    raise WikiError(f"Symlinks are not supported in bundles: {path}", "unsafe_path")
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        yield from walk(child, path + "/")
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    yield path
                else:
                    raise WikiError(f"Not a regular file: {path}", "unsafe_path")
        return list(walk(self.fd))


START = "<!-- lkw:current:start -->\n"
END = "<!-- lkw:current:end -->"


def current_index(text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise WikiError("index.md must contain one intact lkw current block", "invalid_index")
    start = text.index(START) + len(START)
    end = text.index(END)
    if end < start:
        raise WikiError("Managed current block markers are reversed", "invalid_index")
    entries = {}
    for line in text[start:end].splitlines():
        match = re.fullmatch(r"- \[([a-z0-9][a-z0-9-]{0,63})\]\((concepts/\1/r[0-9]{6}\.md)\)", line)
        if not match or match[1] in entries:
            raise WikiError("Managed current block was edited; refusing to replace it", "invalid_index")
        entries[match[1]] = match[2]
    if text[start:end] != render_entries(entries):
        raise WikiError("Managed current block was edited; refusing to replace it", "invalid_index")
    return entries, start, end


def render_entries(entries):
    return "".join(f"- [{key}]({entries[key]})\n" for key in sorted(entries))


def init(root):
    path = Path(root)
    if not path.exists():
        path.mkdir(parents=True)
    with Store(path) as store:
        if os.listdir(store.fd):
            raise WikiError("init requires an empty target directory")
        with store.lock():
            if set(os.listdir(store.fd)) != {".lkw.lock"}:
                raise WikiError("init requires an empty target directory")
            store.create("index.md", ("---\nokf_version: '0.2'\n---\n\n# Local knowledge\n\n"
                                      + START + END + "\n").encode())


def capture(root, source, source_id, actor, resource, at, request_id=None):
    from .requests import digest, execute

    if request_id is not None:
        identifier(request_id)
    identifier(source_id)
    single_line(actor, "actor")
    # Explicit input files may live outside the bundle; no decoding or newline conversion.
    data = read_input(source)
    metadata = {"id": source_id, "original_name": Path(source).name,
                "resource": resource, "captured": {"by": actor, "at": at},
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    folder = f"sources/{source_id}"
    provenance = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode() if request_id is not None else None
    with Store(root) as store, store.lock():
        current_index(store.read("index.md").decode("utf-8"))
        def precondition():
            if request_id is not None:
                try:
                    with store.parent(folder) as (fd, name):
                        os.stat(name, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    return
                raise WikiError("Source ID already exists", "already_exists")

        def mutate():
            # Reserve the whole source directory before either file is written.
            with store.parent(folder, create=True) as (fd, name):
                os.mkdir(name, dir_fd=fd)
            store.create(folder + "/content.raw", data)
            store.create(folder + "/provenance.json", provenance if provenance is not None else
                         (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode())
            return folder + "/content.raw"

        payload = {"id": source_id, "actor": actor, "resource": resource,
                   "original_name": Path(source).name, "sha256": digest(data)}
        return execute(store, request_id, "capture", payload, precondition, mutate)
