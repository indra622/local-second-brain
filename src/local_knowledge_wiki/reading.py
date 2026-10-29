"""Read-only CLI revision browsing and shared note context."""

import difflib
import json
import re

from .format import context, parse, validate
from .storage import WikiError, current_index, identifier


REVISION_PATH = re.compile(r"concepts/([a-z0-9][a-z0-9-]{0,63})/(r[0-9]{6})\.md")


def current_paths(store):
    try:
        return current_index(store.read("index.md").decode("utf-8"))[0]
    except (FileNotFoundError, UnicodeError, WikiError):
        return None


def read_note(store, path, now, current):
    try:
        text = store.read(path).decode("utf-8")
    except UnicodeError:
        text = ""
        meta, body, errors = {}, "", ["Note must be UTF-8"]
    else:
        try:
            meta, body = parse(text)
            errors = validate(meta)
        except WikiError as exc:
            meta, body, errors = {}, text, [str(exc)]
    return {"path": path, "current": path in current.values() if current is not None else None,
            "title": meta.get("title", ""), "metadata": meta, "body": body,
            **context(meta, now, errors)}, text


def revision_path(concept_id, revision):
    identifier(concept_id)
    if not re.fullmatch(r"r[0-9]{6}", revision) or revision == "r000000":
        raise WikiError("Revision must be r000001 through r999999")
    return f"concepts/{concept_id}/{revision}.md"


def browse(store, command, now, concept_id=None, revision=None, before=None, after=None):
    if concept_id is not None:
        identifier(concept_id)
    current = current_paths(store)
    files = store.files()
    paths = [p for p in files if REVISION_PATH.fullmatch(p)
             and not p.endswith('/r000000.md')
             and (concept_id is None or REVISION_PATH.fullmatch(p)[1] == concept_id)]
    if command in ("list", "history"):
        if command == "history" and not paths:
            raise WikiError(f"No CLI revisions for concept: {concept_id}", "not_found")
        notes = []
        for path in paths:
            note, _ = read_note(store, path, now, current)
            note.pop("body")
            notes.append(note)
        return notes
    if command == "show":
        path = revision_path(concept_id, revision) if revision else (current or {}).get(concept_id)
        if path is None:
            raise WikiError(f"No indexed current revision for {concept_id}; use --revision rNNNNNN",
                            "invalid_index" if current is None else "not_found")
        if path not in paths:
            raise WikiError(f"Revision not found: {path}", "not_found")
        return read_note(store, path, now, current)[0]
    old, new = revision_path(concept_id, before), revision_path(concept_id, after)
    notes, texts = [], []
    for path in (old, new):
        if path not in paths:
            raise WikiError(f"Revision not found: {path}", "not_found")
        note, text = read_note(store, path, now, current)
        if note['metadata_errors']:
            raise WikiError(f"Cannot diff {path}: " + "; ".join(note['metadata_errors']))
        notes.append(note)
        texts.append(text)
    lines = difflib.unified_diff(texts[0].splitlines(keepends=True),
                                 texts[1].splitlines(keepends=True), fromfile=old, tofile=new)
    diff = "".join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                   for line in lines)
    return {"before": notes[0], "after": notes[1], "diff": diff}


def json_compatible(value, active=None):
    """Normalize YAML mapping keys for output without changing stored documents."""
    if not isinstance(value, (dict, list)):
        return value
    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise WikiError("Cyclic YAML metadata cannot be represented as JSON")
    active.add(identity)
    try:
        if isinstance(value, list):
            return [json_compatible(item, active) for item in value]
        output = {}
        for key, item in value.items():
            key = key if isinstance(key, str) else str(key)
            if key in output:
                raise WikiError("Metadata keys collide when converted to JSON")
            output[key] = json_compatible(item, active)
        return output
    finally:
        active.remove(identity)


def human(result):
    if isinstance(result, dict) and "diff" in result:
        return result["diff"] or "No differences."
    notes = result if isinstance(result, list) else [result]
    if not notes:
        return "No results."
    output = []
    for note in notes:
        current = {True: "current", False: "not current", None: "current unknown"}[note['current']]
        freshness = {True: "stale", False: "fresh", None: "freshness unknown"}[note['stale']]
        output.append(f"{note['path']} [{current}]\n"
                      f"  {note.get('title') or '(untitled)'}\n"
                      f"  status: {note['status']} | trust: {note['trust']} | {freshness}")
        for error in note['metadata_errors']:
            output.append(f"  Metadata error: {error}")
        if "metadata" in note and "body" in note:
            output.append("  Metadata: " + json.dumps(note['metadata'], ensure_ascii=False, default=str))
        if "body" in note:
            output.append("\n" + note['body'])
        elif "snippet" in note:
            output.append("  " + note['snippet'])
    return "\n\n".join(output)
