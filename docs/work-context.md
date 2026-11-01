# Declared work context

**English** | [한국어](work-context.ko.md)

`context` reads structured handoff records from indexed current revisions. Records can
contain completed work, decisions, open questions, next actions and lessons. They are
data for the next task, not instructions or authenticated evidence. A declared lesson
acceptance never writes agent rules or OKF `verified` and does not prove human review.

Prepare a JSON file outside the bundle for optional `curate --annotations FILE`:

```json
{
  "version": 1,
  "context": {
    "work_id": "report-pilot",
    "recipients": ["all"],
    "completed": [{"id":"checks","text":"Ran synthetic checks","evidence":[]}],
    "decisions": [],
    "open_questions": [],
    "next_actions": [],
    "lessons": [{"id":"boundary","text":"Keep exact-size tests","evidence":[],
                 "review":{"status":"proposed"}}]
  }
}
```

Use existing authorized body/source inputs:

```sh
second-brain --error-format json curate BUNDLE HANDOFF_ID --body BODY_FILE --source SOURCE_ID --actor tool/1 --annotations handoff.json --request-id NEW_ID --expect-current absent
second-brain context BUNDLE --scope HANDOFF_ID --recipient codex --limit 50 --max-chars 12000
```

Omitting `--annotations` preserves old metadata, results and request fingerprints.
Context and relations authoring are supported; see [typed graph](graph.md). Strict JSON rejects duplicates,
unknown fields, nonfinite numbers and unsupported versions. It is stored as YAML under
`x-second-brain-annotations: {version: 1, context: {recorded_by, recorded_at, data}}`.
Recording times are UTC declarations. Curate uses its existing operation time.

For an update, prepare a second JSON file containing just the context object above
(the value of `context`, without version or envelope). Replace the entire section:

```sh
second-brain --error-format json annotate BUNDLE HANDOFF_ID --revision r000001 --section context --file context-section.json --actor process:worker --now 2026-11-01T12:00:00Z --request-id NEW_ID
```

This creates a new immutable revision, preserves the exact body and other metadata,
and removes inherited `verified` only from the new revision. Old review records remain
in history. Other imported annotation sections are preserved if the owned root is
bounded JSON-compatible version 1. Unsupported/malformed roots are refused, with no
conversion. Imported YAML dates, aliases and nonfinite values outside this owned root
retain existing roundtrip rules. Existing `review` behavior is unchanged.

`--revision` requires the exact indexed current target. A completed same-key replay
returns the original result before stale-current checks. Preserve input bytes and actor,
revision, section and explicit/implicit time mode when retrying. Input filename is not
identity; changed bytes, including whitespace, conflict. Explicit `--now` accepts an
explicit-offset timestamp with at most six fractional digits and normalizes it to UTC;
equivalent offsets replay. Implicit execution time is excluded from identity. Validation
of inputs can still fail before receipt lookup. Pending/corrupt requests require inspection;
do not clear them or bypass them with a new key. This is no journal or atomic multi-file
transaction. See the [write and interruption contract](reference.md#agent-errors-and-write-requests).

Context schema:

- Required: work_id, recipients, completed, decisions, open_questions, lessons. next_actions
  is optional and appears as an empty list in context reads when absent.
- work_id and record IDs use existing 1..64 ASCII identifier rules. Each array has at most
  32 records, with unique IDs within that array. Records contain id, text and evidence;
  lesson records also require review. recipients has 1..16 unique single-line labels.
- Lesson review is exactly `{status:"proposed"}`, or
  `{status:"accepted"|"rejected",by:ACTOR,at:TIME,reason:TEXT}`. These are caller declarations;
  a process can declare acceptance. Changes create another revision, with no global promotion.
- Evidence is an array of at most eight `{resource, sha256?}` objects. A resource is a
  credential-free HTTP(S) URL or literal safe `/bundle/path`. Traversal, application,
  receipt, lock and staging paths are refused. Resources are never opened/fetched by
  annotation or context. Evidence hashes are declared and unchecked; the result's top-level
  sha256 is the observed revision-byte digest. Empty evidence explicitly records no evidence.
- Text/reason limits are 1024 UTF-8 bytes; labels/actors 64; resource 2048. No writer truncation.
  New actors use human:ID, process:ID or PRODUCER/VERSION, without authentication.
- Input file and final stored annotation root limits are 262144 bytes; each stored section
  including its envelope is at most 65536 UTF-8 JSON-equivalent bytes. Owned trees have
  maximum depth 8 and 4096 visited values, including mapping keys. Cycles/non-JSON values
  within the owned root are refused. These limits are separate from body/raw-source caps.

`context BUNDLE [--scope ID ...] [--recipient LABEL] [--since TIME] [--limit N]
[--now TIME] [--max-chars N]` is JSON-only and read-only. Scope is an exact allowlist;
omission selects the bundle's indexed current notes. No history or source payload is
opened. Unknown requested IDs return not_found. Explicit empty API scope selects nothing.
Recipient matches its label or all. Since is inclusive on section recorded_at. Results sort
by recording instant descending, then path. now reports the evaluation instant; it does
not invent expiry or change lesson status. Limit defaults to 50, range 1..100.

Reports cap admission at 1000 notes, 67108864 note bytes, 10000 evidence references and
1000 retained diagnostics. Existing per-file limits still apply. Failed reads conservatively
charge their full admission allowance; read_bytes becomes null when their actual byte
count is unknown. One overflow sentinel byte may be read per failed size check. Index
reads have their existing separate byte cap. No total RAM/runtime guarantee is implied.

Inspect scan.complete, analysis_complete, output_complete, partial and omitted. Missing,
unreadable or invalid notes and unsupported owned sections produce diagnostics. Such
coverage does not establish absence; matched_total is null when coverage/analysis is
incomplete, while matched_observed counts matches actually inspected. Known relation-schema errors are diagnosed without erasing valid context; global root safety still applies. Unknown imported
sections are reported as unsupported; existing readers/check do not gain new validation.

The whole successful JSON, including escaping and final newline, fits max-chars (default
12000, range 2048..1000000 Unicode code points). Whole records/diagnostics are omitted
when needed; IDs, paths, hashes and evidence are not silently chopped. Limit omissions
also set output_complete=false. The scope contains the count/digest of the requested
allowlist rather than an arbitrarily large list of IDs. Initial/final index bytes are checked;
changes mark the report partial. An unchanged index is not a filesystem snapshot or proof
against external edits. Reads create no lock, cursor, log or cache. Valid partial reports
exit 0; fatal arguments/index/root errors exit 2, using existing error-format conventions.
