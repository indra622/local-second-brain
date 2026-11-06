# Optional local monitoring view

[한국어](webview.ko.md)

From an installed environment, explicitly select one Local Second Brain CLI bundle:

```sh
second-brain view /absolute/path/to/bundle --port 8765
```

Open the printed `http://127.0.0.1:8765/` address in your browser. Use `--port 0` to
choose an available port. Stop with Ctrl-C. The command does not open your browser,
install anything or discover vaults. It serves one existing CLI bundle, not an arbitrary
Obsidian vault. There are no required dependencies beyond Python and PyYAML, and no
runtime model calls or external assets. Existing commands and storage formats are unchanged.

The Korean-first view provides current-title/body substring search and lifecycle,
review-declaration and freshness filters. Search covers the delivered current notes only,
not raw sources or historical bodies. View actual revisions side by side, textual body
and metadata differences, preserved sources/provenance and supported links or declared
relations. Equal bodies do not prove a review event; inspect the declarations. Source and
note attribution remains explicit text/declarations, not authenticated authorship.

Manual refresh shows scan time and the last successful refresh. A failed refresh keeps
the last successful screen with a visible failure notice. Current selection follows the
index after refresh unless you deliberately opened history. Current does not mean true
or up to date. Missing deadlines remain unknown; actor and review fields are declarations.

## Scope and safety

The server binds only `127.0.0.1`. It accepts the exact printed Host and, when present,
the same Origin; cross-site fetches, permissive CORS and write methods are not supported.
Use the numeric loopback URL, not `localhost`. There is no network bind or public-origin
option. Portal/reverse-proxy delivery is not validated in v01; do not expose the port or
rewrite security headers to make it public. URL assets are relative, but this alone does
not establish proxy compatibility. Stop the viewer when it is not needed. This is a local
reading tool, not an authentication boundary against other programs on your computer.

Only fixed UI assets and one snapshot API are served. No arbitrary file endpoint exists.
Stored Markdown, HTML, scripts, URLs and source text remain text; navigation buttons can
only open loaded revisions. Source bytes are read only when a declared ID and resource
resolve to the matching canonical `sources/ID/content.raw`; unsupported or resource-only
references stay unverified, without guessed file reads. No URLs are fetched.

Reads reuse descriptor-based Store access without locks or writes. Symlinks in the root,
selected concept directories or read paths are refused. No lock, cache, index, receipt or
`.obsidian` file is created. Files and index are checked again before returning a scan;
this detects observed movement but is not a multi-file atomic transaction. Stop or retry
if another writer moves data. A root replacement requires restarting the viewer.

Each scan admits at most 100 indexed concepts, 256 revisions, 128 sources, 512 entries
per selected directory, 512 KiB per file, 8 MiB total input and 12 MiB response. Metadata
conversion has a 4096-visit / 16-depth bound before YAML aliases can expand. Exceeding a
read or output limit fails the refresh rather than silently reporting zero. Missing
current files and bounded related-link output have explicit partial/unknown states.
Unindexed concepts and unrelated directories are not scanned. Link parsing shares the
[graph parser's documented subset](graph.md#read-scope-and-parser); lack of a displayed
edge does not establish a semantic non-relationship. Related links are not fetched to
prove absence outside the loaded scope. Raw non-UTF-8 source files show availability and
hash information without pretending to decode them.

## Validation

Run `python -m unittest discover -s tests -p test_webview.py -v` for boundary and read-only
regressions. The feature adds no editor, ingestion, migration or separate review-event
store. [Design guidance](../DESIGN.md) describes the reading surface. Browser checks must
use public synthetic data and an isolated profile; a successful HTTP fetch alone does
not demonstrate rendered usability.

## Status home

The first view is a compact status dashboard. Its current-note distributions, unique
current source bindings and recent records use the delivered snapshot only. Panels drill
into the existing explorer. Loaded revisions include history for indexed concepts; they
are not counted as current knowledge. Missing files and malformed records remain separate
from unspecified deadlines. Review counts are declarations, not authenticated checks.
Recent rows sort parseable declared generation times across loaded revisions, not observed
usage events. There are no uptime, growth, cost or confidence metrics and no automatic
refresh. Failed refresh retains the last successful home as well as explorer.

Run `node tests/test_webview_ui.cjs` for aggregation and refresh-selection regressions.

Home categories are live filters: successful refresh re-evaluates deadline, review, status,
source and attention membership from the new snapshot. Manual controls intersect that
category. No matching result clears the detail pane. Deliberately opening a record or
history creates an explicit record selection, retained only while it remains in the
loaded scope; it is not a frozen category.

Validated generation times are projected to ISO timestamps with their explicit offsets
for the browser. Equivalent quoted/unquoted YAML timestamps therefore participate in
the same recent ordering. Invalid or timezone-naive declarations remain unknown. This
normalization does not rewrite stored metadata, unknown fields or source bytes.
