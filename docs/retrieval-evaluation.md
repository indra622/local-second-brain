# Evaluate explicit retrieval judgments

**English** | [한국어](retrieval-evaluation.ko.md)

`eval-retrieval` measures what recall actually delivers for questions with explicitly
judged answers. It does not generate labels, upload notes, run an external engine or
add semantic search. Missing answers and mode regressions remain visible. A small
synthetic score is not evidence of general user relevance.

```sh
second-brain eval-retrieval BUNDLE --cases cases.json --mode auto:frequency --mode auto:bm25 --k 1 --k 3 --result-max-chars 12000 --max-chars 12000 --now 2026-11-02T12:00:00Z
```

Author/review the labels yourself; [the example](../examples/retrieval-cases.json) assumes
you created a distinct task-report-pilot concept containing the relevant report decision.
It is not an oracle for your bundle. The development benchmark's separate synthetic
labels are not loaded by default. --cases is always required.

Case JSON has exactly version=integer1, target_mode=current_id|exact_revision, and
1..100 cases. Each case has unique ASCII id, nonempty tokenizable query and gold list.
Queries are <=65536 UTF-8 bytes; input <=2097152 bytes, depth<=8 and <=50000 visited values
including object keys. Duplicate JSON keys, nonfinite values, unknown fields and invalid
UTF-8 are refused. These control limits do not change legacy recall query acceptance.

Current-ID gold is `{id:ID}`; exact-revision gold is `{id:ID,revision:rNNNNNN,sha256?:HEX}`.
Gold has <=32 distinct targets; duplicates (even differently hashed identical pins) are
rejected. current_id resolves to this run's index, not the highest revision. A stale pin,
hash mismatch, absent/unavailable or excluded-scope gold is an invalid judgment for this
run, not an ordinary retrieval miss. Empty gold requires expect_no_match=true and is a
separate control. Nonempty gold cannot be a no-match control. Labels are never rewritten.

The evaluator reads the index, then each selected current note once, and checks final
index bytes. --scope is an exact repeatable ID allowlist; omitted means all indexed
current notes, explicit empty API scope means none. Unknown requested IDs fail not_found.
No history, raw source or excluded note payload is opened. The frozen in-memory read set
uses legacy recall parsing/exclusions, including malformed metadata and imported dates,
sets, NaN and aliases; no owned-annotation/graph validators filter the corpus. All modes
and cases use the same evaluated_at, cases digest, initial index digest and sorted
path/content-hash manifest. On partial scans the manifest identifies only observed reads.
Best-effort capture is not an atomic filesystem snapshot or a persistent cache.

Admission caps are 1000 notes and67108864 note payload bytes, with existing per-file
limits. Failed reads charge their full admission allowance conservatively; unknown actual
read_bytes is null. Oversize/growing files remain bounded, with detection sentinel overhead.
Unread/unsupported/invalid-UTF8 records and index movement make corpus coverage incomplete.
Invalid metadata alone retains legacy recall behavior and is disclosed, not silently removed.
No total RAM/runtime guarantee is claimed. Scoring remains per-note/two-pass BM25, without
retaining note-by-query matrices. Cases/modes are evaluated sequentially and full recall
body results are discarded after extracting delivered identities/diagnostics.

Modes are the six auto/exact/lexical × frequency/bm25 combinations, repeatable and
order-preserving after deduplication. Default auto:frequency preserves the shipped default;
no ranking parameters changed. k defaults to1,3,5,10, allowed1..100. Recall runs at limit=max(k)
and result-max-chars (default12000, range2048..1000000). Metrics use those actual delivered
results, not ideal internal ranks. Result-count budget omissions are distinguished from
answers absent/beyond the horizon; omitted_results also includes limit omissions.

Per-case Recall@k = distinct golds in delivered top k / ALL distinct judged golds.
Macro Recall@k averages the labeled cases. MRR@K is reciprocal first-gold rank inside
K=max(k), otherwise0; horizon_k makes the truncation explicit. Missing gold paths, ranks,
match/fallback mode, exclusions and delivery omissions are reported per case/mode. Empty-gold
controls do not enter relevance denominators; no_match_accuracy uses matched=0, so an empty
output caused by a budget does not become a false successful control.

Incomplete corpus, any invalid label or per-case execution failure makes every primary
aggregate null, with reasons/counts. Completed per-case metrics remain available, but there
is no successful-subset headline. A control-only suite has null relevance metrics and
separate accuracy. Modes compare to the first on the same labeled cases using Recall@K,
then MRR@K; improved/regressed/unchanged/unscorable is explicit per case and summary.

All computation precedes report packing. Entire JSON including escaping/final newline
fits max-chars (default12000, range2048..1000000). Whole mode summaries/diagnostics/cases
may be omitted, with counts, rather than truncating identities or changing denominators.
Large k/mode matrices may require a larger report budget to see all aggregate records.
Output omissions are separate from scan/analysis incompleteness. Valid partial reports
exit0; fatal input/index/root errors exit2 under existing error-format conventions.

Use [task-local workflows](../templates/task-workflow.md) to collect context, inspect
structure/health and explicitly judge reuse. Existing recall does not index annotations,
and evaluation does not install hooks, run schedulers, modify rules or repair notes.
