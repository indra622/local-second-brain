"""Minimal CLI; synthesis belongs to the user's agent."""

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from functools import partial
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from .errors import ErrorParser, emit_error, machine_errors
from .format import (inspect_bundle, nonempty, parse, serialize_revision, timestamp, validate,
                     validate_revision)
from .reading import browse, current_paths, human, json_compatible, read_note, revision_path
from .recall import recall, render
from .requests import digest, encoded, execute, expected_current, validate_expected
from .storage import (Store, WikiError, capture, current_index, identifier, init,
                      read_input, render_entries, single_line)


def curate(root, concept_id, body_file, sources, actor, now, kind, title, status, stale_after,
           request_id=None, expect_current=None):
    if request_id is not None:
        identifier(request_id)
    validate_expected(expect_current)
    identifier(concept_id)
    single_line(kind, "type")
    single_line(actor, "actor")
    if title is not None:
        single_line(title, "title")
    body_bytes = read_input(body_file)
    body = body_bytes.decode("utf-8")
    if body.startswith("---\n") or body.startswith("---\r\n"):
        raise WikiError("Pass a prepared Markdown body without YAML frontmatter")
    meta = {"type": kind, "title": title or concept_id, "status": status,
            "generated": {"by": actor, "at": now}, "sources": []}
    if stale_after:
        timestamp(stale_after)
        meta["stale_after"] = stale_after
    for source in sources:
        identifier(source)
        meta["sources"].append({"id": source, "resource": f"../../sources/{source}/content.raw"})
    errors = validate(meta)
    if errors:
        raise WikiError("; ".join(errors))
    data = serialize_revision(meta, body)
    with Store(root) as store, store.lock():
        before = store.read("index.md")
        index = before.decode("utf-8")
        entries, start, end = current_index(index)
        source_hashes = []
        for source in sources:
            content = store.read(f"sources/{source}/content.raw")
            provenance = store.read(f"sources/{source}/provenance.json")
            source_hashes.append([source, digest(content), digest(provenance)])
        payload = {"id": concept_id, "body_sha256": digest(body_bytes), "sources": source_hashes,
                   "actor": actor, "type": kind, "title": title or concept_id, "status": status,
                   "stale_after": stale_after, "expect_current": expect_current}

        def precondition():
            expected_current(entries, concept_id, expect_current)
            if request_id is not None:
                store.files()

        return execute(store, request_id, "curate", payload, precondition,
                       lambda: write_revision(store, concept_id, meta, body, before, index, entries, start, end, data))


def write_revision(store, concept_id, meta, body, before, index, entries, start, end, data=None):
    """Caller holds the bundle lock and has validated inputs."""
    data = serialize_revision(meta, body) if data is None else data
    validate_revision(data, meta, body)
    files = store.files()
    prefix = f"concepts/{concept_id}/r"
    numbers = [int(p[-9:-3]) for p in files
               if re.fullmatch(re.escape(prefix) + r"[0-9]{6}\.md", p)]
    revision = max(numbers, default=0) + 1
    if revision > 999999:
        raise WikiError("Revision limit reached")
    path = prefix + f"{revision:06}.md"
    entries[concept_id] = path
    store.create(path, data)
    store.replace_index(before, (index[:start] + render_entries(entries) + index[end:]).encode())
    return path


def review_evidence(store, resource):
    if (not nonempty(resource) or resource != resource.strip()
            or any(unicodedata.category(c).startswith("C") for c in resource)):
        raise WikiError("Evidence must be a nonempty URL or bundle-local artifact path")
    parsed = urlsplit(resource)
    if parsed.scheme:
        if (parsed.scheme not in ("http", "https") or not parsed.netloc or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(c.isspace() or c in '<>"{}|^`\\' for c in resource)
                or re.search(r"%(?![0-9a-fA-F]{2})", resource)):
            raise WikiError("Evidence URL must be an absolute http(s) URL without credentials")
        if parsed.netloc.startswith("[") and not re.fullmatch(r"\[[^\]]+\](?::[0-9]+)?", parsed.netloc):
            raise WikiError("Invalid evidence URL authority")
        host = parsed.hostname.encode("idna").decode("ascii")
        if ":" not in host and not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                                        for label in host.rstrip(".").split(".")):
            raise WikiError("Invalid evidence URL host")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise WikiError("Invalid evidence URL port")
        if parsed.netloc.endswith(":"):
            raise WikiError("Invalid evidence URL port")
        return {"resource": resource}
    path = resource[1:] if resource.startswith("/") else resource
    if (parsed.netloc or parsed.query or parsed.fragment or "?" in resource or "#" in resource
            or "\\" in resource or any(p in ("", ".", "..", ".git", ".obsidian") for p in path.split("/"))):
        raise WikiError("Unsafe evidence path; use a literal bundle-root artifact path")
    data = store.read(path)
    if not data:
        raise WikiError("Local evidence artifact must not be empty")
    return {"resource": "/" + path, "sha256": hashlib.sha256(data).hexdigest()}


def review(root, concept_id, revision, actor, evidence, request_id=None):
    if request_id is not None:
        identifier(request_id)
    target = revision_path(concept_id, revision)
    if not re.fullmatch(r"(?:human:[^\s:/\\]+|process:[^\s:/\\]+|[^\s:/\\]+/[^\s:/\\]+)", actor) or any(
            unicodedata.category(c).startswith("C") for c in actor):
        raise WikiError("Review actor must be human:ID, process:ID or PRODUCER/VERSION")
    with Store(root) as store, store.lock():
        before = store.read("index.md")
        index = before.decode("utf-8")
        entries, start, end = current_index(index)
        if request_id is None and entries.get(concept_id) != target:
            raise WikiError("Review target must be the exact indexed current revision", "precondition_failed")
        original = store.read(target)
        meta, body = parse(original.decode("utf-8"))
        errors = validate(meta)
        if errors:
            raise WikiError("; ".join(errors))
        json_compatible(meta)
        reference = review_evidence(store, evidence)
        payload = {"id": concept_id, "revision": revision, "actor": actor, "evidence": evidence,
                   "reference": reference, "target_sha256": digest(original)}

        def precondition():
            if entries.get(concept_id) != target:
                raise WikiError("Review target must be the exact indexed current revision", "precondition_failed")
            if request_id is not None:
                store.files()
                if len(encoded(json_compatible(meta.get("verified", [])))) > 7000000:
                    raise WikiError("Review records are too large for a request receipt")

        events = meta.get("verified", [])
        events = [events] if isinstance(events, dict) else list(events)
        events.append({"by": actor, "at": datetime.now(timezone.utc).isoformat(),
                       "x-second-brain-target": {"resource": "/" + target,
                                                 "sha256": hashlib.sha256(original).hexdigest()},
                       "x-second-brain-evidence": reference})
        meta["verified"] = events
        data = serialize_revision(meta, body)

        def mutate():
            if store.read(target) != original or store.read("index.md") != before:
                raise WikiError("Review target or index.md changed during this operation", "concurrent_change")
            path = write_revision(store, concept_id, meta, body, before, index, entries, start, end, data)
            return {"revision": path, "verified": json_compatible(events) if request_id else events}

        return execute(store, request_id, "review", payload, precondition, mutate)


def search(root, query, now, current_only=False, status=None, freshness=None):
    terms = set(re.findall(r"\w+", query.casefold()))
    if not terms:
        raise WikiError("Query needs at least one word")
    results = []
    with Store(root) as store:
        current = current_paths(store)
        for path in store.files():
            if not path.endswith(".md") or PurePosixPath(path).name in ("index.md", "log.md"):
                continue
            note, _ = read_note(store, path, now, current)
            counts = Counter(re.findall(r"\w+", (str(note['title']) + "\n" + note['body']).casefold()))
            if not terms <= counts.keys():
                continue
            if current_only and note['current'] is not True:
                continue
            if status and (note['metadata_errors'] or note['status'] != status):
                continue
            state = {True: "stale", False: "fresh", None: "unknown"}[note['stale']]
            if freshness and state != freshness:
                continue
            snippet = " ".join(note.pop('body').split())
            note.pop('metadata')
            results.append({**note, "score": sum(counts[t] for t in terms),
                            "snippet": snippet[:159] + "…" if len(snippet) > 160 else snippet})
    return sorted(results, key=lambda item: (-item["score"], item["path"]))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    machine = machine_errors(argv)
    parser = ErrorParser(prog="second-brain", machine=machine)
    parser.add_argument("--error-format", choices=("legacy", "json"), default="legacy",
                        help="Error interface; put before COMMAND (default legacy); json includes parser errors")
    commands = parser.add_subparsers(dest="command", required=True,
                                    parser_class=partial(ErrorParser, machine=machine))
    p = commands.add_parser("init", help="Create an empty bundle")
    p.add_argument("bundle")
    p = commands.add_parser("capture", help="Copy source bytes and record provenance")
    p.add_argument("bundle")
    p.add_argument("file")
    p.add_argument("--id", required=True)
    p.add_argument("--actor", required=True, help="Declared actor, single line")
    p.add_argument("--resource", required=True)
    p.add_argument("--request-id", help="Bundle-wide retry ID, 1..64 lowercase ASCII letters/digits/hyphens; preserve original payload")
    p = commands.add_parser("curate", help="Store a prepared body as a new revision")
    p.add_argument("bundle")
    p.add_argument("id")
    p.add_argument("--body", required=True)
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--actor", required=True, help="Declared actor, single line")
    p.add_argument("--type", default="Concept", help="Single-line type (default Concept)")
    p.add_argument("--title", help="Single-line title (default concept ID)")
    p.add_argument("--status", choices=("draft", "stable", "deprecated"), default="draft")
    p.add_argument("--stale-after")
    p.add_argument("--request-id", help="Bundle-wide retry ID; replay original result before checking expected current")
    p.add_argument("--expect-current", help="Require indexed rNNNNNN or absent under the write lock")
    p = commands.add_parser("review", help="Record a declared review of the exact current revision; no factual check")
    p.add_argument("bundle")
    p.add_argument("id")
    p.add_argument("--revision", required=True, help="Exact indexed current revision rNNNNNN")
    p.add_argument("--actor", required=True, help="Declared human:ID, process:ID or PRODUCER/VERSION; not authenticated")
    p.add_argument("--request-id", help="Bundle-wide retry ID; same exact revision/evidence/actor replays prior review")
    p.add_argument("--evidence", required=True, help="Absolute http(s) URL or bundle-root regular artifact path; never fetched or executed")
    p = commands.add_parser("recall", help="Bounded current context as JSON; exact-first with disclosed prefix fallback")
    p.add_argument("bundle")
    p.add_argument("query")
    p.add_argument("--match", choices=("auto", "exact", "lexical"), default="auto",
                   help="auto: exact then lexical only on miss; lexical: word prefixes, 2+ Hangul syllables or 3+ other characters; all terms required")
    p.add_argument("--limit", type=int, default=5, help="Maximum results, 1..100 (default 5)")
    p.add_argument("--max-chars", type=int, default=12000,
                   help="Entire JSON output budget including newline, Unicode code points, not tokens; 2048..1000000 (default 12000)")
    p.add_argument("--now", help="Explicit-offset ISO8601 evaluation instant")
    p = commands.add_parser("search", help="Search every concept revision using exact words")
    p.add_argument("bundle")
    p.add_argument("query")
    p.add_argument("--now", help="Explicit-offset ISO8601 evaluation instant")
    p.add_argument("--current-only", action="store_true", help="Require an indexed current revision")
    p.add_argument("--status", choices=("draft", "stable", "deprecated"),
                   help="Filter lifecycle status; exclude invalid metadata")
    p.add_argument("--freshness", choices=("fresh", "stale", "unknown"),
                   help="Filter by usable stale_after deadline")
    p.add_argument("--format", choices=("json", "text"), default="json")
    for command in ("list", "show", "history", "diff"):
        p = commands.add_parser(command, help="Browse CLI concept revisions (read-only)")
        p.add_argument("bundle")
        if command != "list":
            p.add_argument("id")
        if command == "show":
            p.add_argument("--revision", help="Revision rNNNNNN; default is indexed current")
        if command == "diff":
            p.add_argument("before", help="Old revision rNNNNNN")
            p.add_argument("after", help="New revision rNNNNNN")
        p.add_argument("--now", help="Explicit-offset ISO8601 evaluation instant")
        p.add_argument("--format", choices=("json", "text"), default="json")
    p = commands.add_parser("check", help="Check metadata subset, links and freshness")
    p.add_argument("bundle")
    p.add_argument("--now", help="Explicit-offset ISO8601 evaluation instant")
    args = parser.parse_args(argv)
    try:
        now = timestamp(args.now) if getattr(args, "now", None) else datetime.now(timezone.utc)
        for key in ("actor", "resource"):
            if hasattr(args, key) and not nonempty(getattr(args, key)):
                raise WikiError(f"{key} must be a nonempty string")
        if args.command == "init":
            init(args.bundle)
            result = {"bundle": args.bundle}
        elif args.command == "capture":
            result = {"source": capture(args.bundle, args.file, args.id, args.actor,
                                         args.resource, now.isoformat(), args.request_id)}
        elif args.command == "curate":
            result = {"revision": curate(args.bundle, args.id, args.body, args.source,
                                         args.actor, now.isoformat(), args.type, args.title,
                                         args.status, args.stale_after, args.request_id, args.expect_current)}
        elif args.command == "review":
            result = review(args.bundle, args.id, args.revision, args.actor, args.evidence, args.request_id)
        elif args.command == "recall":
            result = recall(args.bundle, args.query, now, args.match, args.limit, args.max_chars)
            print(render(result), end="")
            return 0
        elif args.command == "search":
            result = search(args.bundle, args.query, now, args.current_only, args.status, args.freshness)
        elif args.command in ("list", "show", "history", "diff"):
            with Store(args.bundle) as store:
                result = browse(store, args.command, now, getattr(args, 'id', None),
                                getattr(args, 'revision', None), getattr(args, 'before', None),
                                getattr(args, 'after', None))
        else:
            with Store(args.bundle) as store:
                result = inspect_bundle(store, now)
        result = json_compatible(result)
        if getattr(args, 'request_id', None):
            print(render(result), end="")
        elif getattr(args, 'format', None) == 'text':
            print(human(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 1 if args.command == "check" and result["invalid"] else 0
    except (WikiError, OSError, UnicodeError, ValueError, TypeError) as exc:
        if machine:
            emit_error(exc)
        elif args.command == 'recall' or getattr(args, 'format', None) == 'json':
            print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"second-brain: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if not machine:
            raise
        emit_error(exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
