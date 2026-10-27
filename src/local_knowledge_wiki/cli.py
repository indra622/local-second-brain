"""Minimal CLI; synthesis belongs to the user's agent."""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import PurePosixPath

import yaml

from .format import inspect_bundle, nonempty, timestamp, validate
from .reading import browse, current_paths, human, read_note
from .storage import (Store, WikiError, capture, current_index, identifier, init,
                      read_input, render_entries)


def curate(root, concept_id, body_file, sources, actor, now, kind, title, status, stale_after):
    identifier(concept_id)
    body = read_input(body_file).decode("utf-8")
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
    with Store(root) as store, store.lock():
        before = store.read("index.md")
        index = before.decode("utf-8")
        entries, start, end = current_index(index)
        for source in sources:
            store.read(f"sources/{source}/content.raw")
            store.read(f"sources/{source}/provenance.json")
        files = store.files()
        prefix = f"concepts/{concept_id}/r"
        numbers = [int(p[-9:-3]) for p in files
                   if re.fullmatch(re.escape(prefix) + r"[0-9]{6}\.md", p)]
        revision = max(numbers, default=0) + 1
        if revision > 999999:
            raise WikiError("Revision limit reached")
        path = prefix + f"{revision:06}.md"
        entries[concept_id] = path
        data = ("---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
                + "---\n" + body).encode("utf-8")
        store.create(path, data)
        store.replace_index(before, (index[:start] + render_entries(entries) + index[end:]).encode())
    return path


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
    parser = argparse.ArgumentParser(prog="second-brain")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init", help="Create an empty bundle")
    p.add_argument("bundle")
    p = commands.add_parser("capture", help="Copy source bytes and record provenance")
    p.add_argument("bundle")
    p.add_argument("file")
    p.add_argument("--id", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--resource", required=True)
    p = commands.add_parser("curate", help="Store a prepared body as a new revision")
    p.add_argument("bundle")
    p.add_argument("id")
    p.add_argument("--body", required=True)
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--type", default="Concept")
    p.add_argument("--title")
    p.add_argument("--status", choices=("draft", "stable", "deprecated"), default="draft")
    p.add_argument("--stale-after")
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
                                         args.resource, now.isoformat())}
        elif args.command == "curate":
            result = {"revision": curate(args.bundle, args.id, args.body, args.source,
                                         args.actor, now.isoformat(), args.type, args.title,
                                         args.status, args.stale_after)}
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
        if getattr(args, 'format', None) == 'text':
            print(human(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 1 if args.command == "check" and result["invalid"] else 0
    except (WikiError, OSError, UnicodeError, ValueError, TypeError) as exc:
        if getattr(args, 'format', None) == 'json':
            print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"second-brain: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
