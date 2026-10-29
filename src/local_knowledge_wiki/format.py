"""A documented subset of OKF 0.2, not factual verification."""

import math
import posixpath
import re
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import yaml

from .storage import WikiError


class MetadataLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        try:
            hash(key)
        except TypeError as exc:
            raise WikiError("Unhashable YAML mapping key") from exc
        if key in result:
            raise WikiError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


MetadataLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse(text):
    lines = text.split("\n")
    if not text.startswith(("---\n", "---\r\n")):
        raise WikiError("Missing YAML frontmatter")
    end = next((i for i in range(1, len(lines))
                if lines[i] == "---" or (lines[i] == "---\r" and i < len(lines) - 1)), None)
    if end is None:
        raise WikiError("Unclosed YAML frontmatter")
    try:
        metadata = yaml.load("\n".join(lines[1:end]) + "\n", Loader=MetadataLoader)
    except (yaml.YAMLError, ValueError, RecursionError) as exc:
        raise WikiError(f"Invalid YAML: {exc}") from exc
    if not isinstance(metadata, dict):
        raise WikiError("Frontmatter must be a mapping")
    return metadata, "\n".join(lines[end + 1:])


def yaml_key(value):
    # SafeLoader mapping/set keys are scalars; NaN is not equal to itself.
    return (type(value), None if isinstance(value, float) and math.isnan(value) else value)


def same_metadata(left, right, seen=None):
    if type(left) is not type(right):
        return False
    if isinstance(left, float) and math.isnan(left):
        return math.isnan(right)
    if isinstance(left, (dict, list)):
        seen = set() if seen is None else seen
        pair = (id(left), id(right))
        if pair in seen:
            return True
        seen.add(pair)
        if len(left) != len(right):
            return False
        if isinstance(left, dict):
            other = {yaml_key(key): value for key, value in right.items()}
            return all(yaml_key(key) in other and same_metadata(value, other[yaml_key(key)], seen)
                       for key, value in left.items())
        return all(same_metadata(a, b, seen) for a, b in zip(left, right))
    if isinstance(left, set):
        return len(left) == len(right) and {yaml_key(value) for value in left} == {yaml_key(value) for value in right}
    return left == right


def validate_revision(data, metadata, body):
    loaded, actual_body = parse(data.decode("utf-8"))
    errors = validate(loaded)
    if errors or actual_body != body or not same_metadata(metadata, loaded):
        raise WikiError("Revision serialization must preserve valid metadata and the exact body")


class RevisionDumper(yaml.SafeDumper):
    pass


def revision_string(dumper, value):
    # YAML folds literal NEL in quoted multiline scalars into a space.
    return dumper.represent_scalar('tag:yaml.org,2002:str', value,
                                   style='"' if '\x85' in value else None)


RevisionDumper.add_representer(str, revision_string)


def serialize_revision(metadata, body):
    try:
        data = ("---\n" + yaml.dump(metadata, Dumper=RevisionDumper, allow_unicode=True, sort_keys=False)
                + "---\n" + body).encode("utf-8")
        validate_revision(data, metadata, body)
        return data
    except (yaml.YAMLError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise WikiError("Revision serialization failed validation") from exc


def timestamp(value):
    text = value.isoformat() if isinstance(value, datetime) else value
    if not isinstance(text, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\d[Tt]\d\d:\d\d:\d\d(?:\.\d+)?(?:[Zz]|[+-]\d\d:\d\d)", text
    ):
        raise WikiError("Expected ISO8601 datetime with explicit UTC offset")
    try:
        result = datetime.fromisoformat(text.upper().replace("Z", "+00:00"))
    except ValueError as exc:
        raise WikiError("Invalid datetime") from exc
    return result


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(meta):
    errors = []

    def need_string(obj, key, prefix):
        if not nonempty(obj.get(key)):
            errors.append(prefix + key + " must be a nonempty string")

    def date(obj, key, prefix):
        if key in obj:
            try:
                timestamp(obj[key])
            except WikiError as exc:
                errors.append(prefix + key + ": " + str(exc))

    need_string(meta, "type", "")
    for key in ("title", "description", "resource"):
        if key in meta:
            need_string(meta, key, "")
    if "tags" in meta and (not isinstance(meta["tags"], list)
                           or not all(nonempty(x) for x in meta["tags"])):
        errors.append("tags must be a list of nonempty strings")
    if "status" in meta and meta["status"] not in ("draft", "stable", "deprecated"):
        errors.append("status must be draft, stable or deprecated")
    date(meta, "stale_after", "")
    for family in ("generated", "verified"):
        if family not in meta:
            continue
        events = meta[family]
        if family == "generated" or isinstance(events, dict):
            events = [events]
        if not isinstance(events, list):
            errors.append(f"{family} must be a mapping" + (" or list" if family == "verified" else ""))
            continue
        for event in events:
            if not isinstance(event, dict):
                errors.append(f"{family} entry must be a mapping")
                continue
            need_string(event, "by", family + ".")
            if family == "verified" and "at" not in event:
                errors.append("verified.at is required")
            date(event, "at", family + ".")
    if "sources" in meta:
        if not isinstance(meta["sources"], list):
            errors.append("sources must be a list")
        else:
            for source in meta["sources"]:
                if not isinstance(source, dict):
                    errors.append("sources entry must be a mapping")
                    continue
                need_string(source, "resource", "sources.")
                date(source, "last_modified", "sources.")
    if "usage_window" in meta:
        window = meta["usage_window"]
        if not isinstance(window, dict):
            errors.append("usage_window must be a mapping")
        else:
            for key in ("from", "to"):
                date(window, key, "usage_window.")
    return errors


def context(meta, now, errors):
    events = meta.get("verified", [])
    events = [events] if isinstance(events, dict) else events
    trust = "unverified"
    if errors:
        trust = "invalid-metadata"
    elif events:
        trust = ("human-reviewed" if any(e["by"].startswith("human:") for e in events)
                 else "machine-confirmed")
    stale = None
    if "stale_after" in meta:
        try:
            stale = now >= timestamp(meta["stale_after"])
        except WikiError:
            pass
    return {"status": meta.get("status", "stable"), "trust": trust, "stale": stale,
            "stale_after": meta.get("stale_after"), "generated": meta.get("generated"),
            "verified": meta.get("verified"), "metadata_errors": errors}


def local_target(document, target):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if "\\" in path or "\x00" in path:
        raise WikiError(f"Unsafe link: {target}")
    resolved = posixpath.normpath(path.lstrip("/") if path.startswith("/") else
                                  posixpath.join(posixpath.dirname(document), path))
    if resolved == ".." or resolved.startswith("../"):
        raise WikiError(f"Link escapes bundle: {target}")
    return resolved


def links(body):
    # Only simple inline links outside backtick/tilde fenced blocks are supported.
    fence = None
    for line in body.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield from re.findall(r"\[[^\]\n]*\]\(([^\s()]+)\)", line)


def inspect_bundle(store, now):
    files = store.files()
    available = set(files)
    available.update(str(parent) for f in files for parent in PurePosixPath(f).parents)
    report = {"invalid": [], "warnings": [], "stale": [], "concepts": 0}
    for path in files:
        if not path.endswith(".md"):
            continue
        try:
            text = store.read(path).decode("utf-8")
            name = PurePosixPath(path).name
            resource_links = []
            if name in ("index.md", "log.md"):
                body = text
                if text.startswith("---\n") or text.startswith("---\r\n"):
                    if path != "index.md":
                        raise WikiError("Reserved directory index/log must not have frontmatter")
                    meta, body = parse(text)
                    if "okf_version" in meta and meta["okf_version"] != "0.2":
                        report["warnings"].append({"path": path, "message": "Unknown okf_version"})
            else:
                report["concepts"] += 1
                meta, body = parse(text)
                errors = validate(meta)
                for error in errors:
                    report["invalid"].append({"path": path, "message": error})
                if isinstance(meta.get("sources"), list):
                    for source in meta["sources"]:
                        resource = source.get("resource") if isinstance(source, dict) else None
                        if isinstance(resource, str) and resource.startswith(("./", "../", "/")):
                            resource_links.append(resource)
                if context(meta, now, errors)["stale"]:
                    report["stale"].append(path)
            for target in [*links(body), *resource_links]:
                try:
                    resolved = local_target(path, target)
                    if resolved is not None and resolved not in available:
                        report["warnings"].append({"path": path, "message": "Missing link: " + target})
                except (WikiError, ValueError) as exc:
                    report["warnings"].append({"path": path, "message": str(exc)})
        except (WikiError, UnicodeError, ValueError) as exc:
            report["invalid"].append({"path": path, "message": str(exc)})
    return report
