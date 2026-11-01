# Declared knowledge graph

**English** | [한국어](graph.ko.md)

`graph` shows declared relations and supported Markdown/source links between indexed
current notes. Backlinks and explained directed paths help an agent inspect structural
connections. They do not establish truth, detect semantic contradictions or change recall
ranking. References are never fetched, executed or promoted to instructions.

## Author relations with existing revisions

Optional `curate --annotations FILE` now accepts context, relations, or both. See
[the small author-input example](../examples/graph-relations.json), intended for a subject
such as `decision`, with a separate `reference` concept. A relations data object is:

```json
{"items":[{"id":"basis","type":"depends_on","target":{"id":"reference"},"expectation":"required","evidence":[]}]}
```

For curate, wrap that value in `{"version":1,"relations":RELATIONS_DATA}`. For annotate,
the input file contains just RELATIONS_DATA:

```sh
second-brain --error-format json annotate BUNDLE decision --revision r000001 --section relations --file relations-section.json --actor process:worker --request-id NEW_ID
second-brain graph BUNDLE --scope decision --scope reference
second-brain graph BUNDLE --backlinks reference --relation depends_on
second-brain graph BUNDLE --path decision reference --max-depth 3 --max-chars 12000
```

The existing immutable writer, exact-current base, target/input hashes, actor/time,
receipt/CAS and preflight rules apply. Completed replay precedes stale-current checks;
equal bytes from a renamed input replay, changed bytes conflict. Implicit time stays out
of identity. A new annotation clears inherited verified only on its new revision and
preserves the body/other metadata. Nothing writes a target or a reciprocal relation.

Relations have at most 128 items, each exactly id, type, target, expectation and evidence.
IDs use existing ASCII rules and are unique within the section. Types are fixed:
relates_to, depends_on, supersedes, contradicts, supports. These are caller assertions,
including contradicts; they are not authenticated or independently fact-checked.
Target is `{id:ID}` for a current pointer, or `{id:ID,revision:rNNNNNN}` for a pin.
Expectation is required or wanted; wanted requires an unversioned target. Self-concept,
unknown-type, duplicate-ID and invalid target declarations are refused before intent.
Evidence uses the existing bounded, unchecked reference schema. The existing 262144-byte
input/root, 65536-byte stored section, depth/visit and per-field caps still apply, with
escaped UTF-8 size checked before alias expansion. Missing optional annotation input
continues to add no payload key or metadata.

## Read scope and parser

```text
graph BUNDLE [--scope ID ...] [--backlinks ID | --path FROM TO]
      [--relation TYPE ...] [--max-depth N] [--max-chars N]
```

Scope is an exact indexed-ID allowlist; omission selects indexed current notes. Endpoints
must be selected. Missing scope IDs fail not_found; nonselected endpoints fail invalid_input.
No highest-revision inference, history fallback, title/alias/wikilink matching, raw-source
reads or target filesystem probes occur. Even a target symlink outside scope is not opened.
References inside a note's context or relation evidence do not automatically become edges.

Filters accept the five declared types plus derived link and source. Derived edges keep
separate markdown/sources origins. The graph-specific simple-inline-v1 parser reads
`[label](target)` and image targets without spaces/parentheses. It masks backtick/tilde
fences starting with up to three spaces, through a same-character closing run at least as
long with only trailing whitespace. An unclosed fence masks the remainder. Equal-length
backtick runs delimit inline code, including across unfenced lines; unmatched runs remain
literal. The parser normalizes LF/CRLF/CR only in its working copy for line provenance; stored bodies are unchanged. Fence removal precedes span handling. Backslash escape rules, indented code,
reference links, HTML, nested links, CommonMark and Obsidian alias resolution are not
implemented. The old check parser/output is unchanged. Relative Markdown paths are
normalized with the existing one-decode path rules; fragments are not validated. External
HTTP(S) and other supported resource declarations remain unchecked terminal references.
Unsafe/application/receipt/lock paths are diagnosed. Graph resources are at most 2048
UTF-8 bytes; oversized identities are skipped with a diagnostic, never chopped.

Only selected, successfully parsed current notes enter traversable adjacency. Resolution
states distinguish resolved, out_of_scope, non_current_reference, not_indexed,
wanted_not_indexed, missing_indexed, unavailable_indexed, invalid_indexed and unread_indexed.
A non-current pin does not prove that file exists. not_indexed does not prove no historical
or imported note exists. Wanted unindexed targets are an explicit wishlist, not corruption;
when indexed they resolve normally. Raw sources, assets, free-form source locators and
URLs are unchecked_resource terminals. The root index's exact missing selected file is
reported as missing_indexed, rather than being confused with an unwritten concept.

Edges retain source revision path/hash and resolved target path/hash, declaration actor/time,
relation ID/evidence or Markdown line/source position. Evidence hashes remain declared.
Duplicates group only within the same source/type/origin/target/expectation, with a count
and every admitted provenance entry. Origins are never silently merged or dropped. A large
group may be omitted whole under the output budget.

Backlinks derive incoming edges without reverse writes. Paths use breadth-first traversal
of directed edges, with deterministic path/type/provenance ties. Default depth is 3,
range 1..8; max-depth requires --path. A complete found path is shortest in this scoped
structural model. With incomplete analysis it is found_partial, not a proved shortest path.
No match is no_path_within_depth only with complete adjacency; otherwise undetermined.
A zero-hop path is allowed for a readable selected node. Cycles do not imply factual
contradiction. Path steps keep their original directions and provenance.

## Limits and incomplete reports

The new report caps are 1000 selected notes admitted, 67108864 note payload bytes,
10000 extracted reference occurrences and 1000 retained diagnostics. Old per-file limits
remain. Rejected reads conservatively charge their allowance and may make read_bytes
unknown/null; an overflow sentinel may be consumed. No total RAM/runtime guarantee is
claimed. Scope/read limits can stop before later selected notes; unread_indexed is not
missing. Invalid references also consume reference admission. Type filtering can avoid
unused derived origins; inspected typed declarations still count before filtering.

Known-section schema errors are local: malformed relations do not erase valid context,
and malformed context does not erase graph relations. Diagnostics mark whether they affect
the current analysis. Root version/type/depth/visit/JSON-byte safety remains global. Writers
validate all implemented sections of the candidate root; unknown imported sections retain
the prior bounded preservation contract and are not interpreted. Unknown sections make
coverage incomplete when inspected. No future health/freshness/evaluation validator exists.

Successful JSON includes schema_version, scope count/digest, query/parser, scan counters,
analysis_complete, output_complete, partial, omitted and observed/total counts. Unknown
complete totals are null, not zero. Index bytes are compared before/after; change makes
analysis incomplete. This is best-effort, not an atomic filesystem snapshot. Graph reads
create no lock marker, cursor, log or cache. Diagnostic reports exit 0; fatal input/index/root
errors exit 2 through existing error-format conventions. Help needs no platform capability.

The entire successful stdout, including JSON escaping and final newline, fits max-chars
(default 12000, range 2048..1000000 Unicode code points). Packing selects whole deterministic
prefixes with bounded formatting passes: path explanations first, then diagnostics, edges
and nodes. No identities or digests are clipped. A found path can have its whole explanation
omitted when it will not fit; path_state/path_length and omitted.paths disclose that.
Computed counts do not change when output details are omitted. Existing context JSON packing
and frozen outputs are unchanged. No cache, semantic retrieval or speedup is claimed.
