# Knowledge health declarations

**English** | [한국어](health.ko.md)

`health BUNDLE [--scope ID ...] [--now TIME] [--verify-source ID ...] [--max-chars N]`
reports actionable structural recommendations without changing knowledge. It reads selected
indexed-current notes once, using the graph's bounded extraction/resolution data. It never
calls a model, fetches a URL or repairs/promotes anything. Review, observation time, a current
pointer, retained bytes and declared provenance are different signals.

## Author declarations

Curate accepts optional `--annotations FILE` with version1 and any implemented context,
relations, freshness or source_evidence section. Annotate accepts just the chosen section's
data with `--section freshness` or `--section source_evidence`. Existing exact-current,
immutable revision, verified reset, raw input/target hash, replay/CAS/time and preflight rules
apply. Omitted annotations preserve old fingerprints. Examples of section data:

```json
{"form":"observation","observed_at":"2026-11-01T12:00:00Z","evidence":[]}
```

```json
{"form":"pointer","target":{"resource":"https://example.invalid/current"},"last_observed_at":"2026-11-01T12:00:00Z","recheck_after":"2026-11-08T12:00:00Z","evidence":[]}
```

```json
{"form":"reference","evidence":[]}
```

Observation requires observed_at. Pointer requires target; last_observed_at and recheck_after
are optional. All forms require evidence (maximum8 references, possibly empty). Times are
explicit-offset strings, at most6 fractional digits, normalized to UTC for new writes. An old
observation remains a dated assertion; age is not falsehood. A pointer is due only at its
explicit recheck_after, and a note deadline uses the separate existing stale_after. No
seven-day rule, generated/verified/recorded/mtime substitution or live-state inference exists.
Reference does not mean verified or timeless. Missing evidence and future observations are
reported, without inventing a corrected value.

```json
{"items":[{"resource":"/sources/memo/content.raw","provenance_basis":"derived","retained_scope":"excerpt","rationale":"A declared summary","evidence":[]}]}
```

Source_evidence has <=32 items with exactly resource, provenance_basis, retained_scope,
rationale and evidence. Basis is primary_record/direct_document/derived/unknown; retention is
complete/excerpt/locator_only/unknown. They are declarations, not grades or factual proof.
Resource must match a note.sources resource after safe document-relative normalization or
exact locator equality. New unlinked assessments fail preflight; imported ones are findings.
Disagreeing declarations are exposed, never adjudicated or used to change recall ranking.
Captured files/sidecars are not rewritten. Existing annotation caps apply: input/root262144
bytes, stored section65536 UTF-8 JSON-equivalent bytes, depth8/4096 values; escaped size is
checked before alias expansion. Evidence/actor/text limits remain those of work context.

## Read and check

```sh
second-brain health BUNDLE --scope TASK_ID --now 2026-11-02T12:00:00Z
second-brain health BUNDLE --scope TASK_ID --verify-source memo --max-chars 12000
```

Default health opens no source payload or provenance sidecar. Up to16 distinct explicit
verify-source IDs authorize only `/sources/ID/content.raw` and provenance.json. Reads use
nofollow/nonblocking regular-file checks and chunk hashing; URLs and other evidence paths
are never opened. The aggregate verification budget is134217728 bytes, including sidecars
and failed partial reads. Per-file caps remain raw268435456 and sidecar8000000 bytes. A file
larger than remaining budget is unchecked_budget, not corrupt. Oversized per-file input is
unchecked_limit. Missing/nonregular/unreadable files and invalid provenance are distinct.

Sidecar validation rejects duplicate JSON keys, nonfinite values, boolean/negative byte
counts, wrong IDs/digest shape and malformed capture fields. Old generic single-line actors,
opaque string locators and legacy timestamp precision remain accepted; newer annotation
actor/HTTP-only rules are not imposed. Raw contents and old locator strings are never emitted.
Matched means digest AND byte count match the observed data, not authenticity or truth.
Declared evidence hashes are compared only when they identify an explicitly checked source.
Hash mismatch is an observed finding, not an incomplete scan; inability to check is incomplete.

The one current-note pass inherits1000 notes/64MiB,10000 graph references/1000 diagnostics.
Health also caps inspected evidence references and retained findings at10000 each. Whole
reports disclose scan, analysis and verification completeness separately; expected due,
wanted, unassessed or limited-evidence classifications do not by themselves mean incomplete.
Unread/skipped/schema failures do; unknown total findings are null. Known-section failures
are consumer-local, while root safety is global. No total RAM/time guarantee is implied.

Findings sort by severity/path/field/kind and contain an action recommendation. Wanted,
required unindexed, non-current, excluded, broken indexed and unchecked source references
remain different. No physical/history absence or semantic contradiction is inferred. The
reader is best-effort and checks index movement; it is not an atomic snapshot.

JSON, including escaping and final newline, fits max-chars (default12000,2048..1000000 code
points). Efficient prefix packing omits whole diagnostics/checks/findings with explicit counts;
identities/digests are not silently truncated. Counts are computed before output omission.
Valid diagnostic reports exit0, fatal arguments/index/root errors exit2 under existing error
formats. No lock/cursor/cache/log or rule is created. Legacy check, inspect-storage, context,
graph and recall contracts remain; evaluation is not implemented by this feature.
