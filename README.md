# Local Second Brain

**English** | [한국어](README.ko.md)

**Early alpha: validated on macOS. Windows is not supported. Linux is unvalidated.**

**Your second brain. Local files. Any agent.**

Keep knowledge, not just chat history. Local Second Brain preserves the sources,
review records, freshness signals, and revisions behind your notes, in files you own.
It follows an LLM Wiki-style workflow and uses a documented subset of
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).

- **Trace knowledge to its sources.** Keep original bytes and capture records, then link notes to them.
- **See what has been reviewed.** Distinguish authorship from recorded verification. A format check is not a fact check.
- **Spot stale knowledge.** Read generation times and optional expiry dates alongside search results.
- **Keep earlier decisions.** Write a new revision without changing earlier files. The index points to the current revision.
- **Change agents, keep your knowledge.** Use ordinary files and Markdown, without a required model, service, or agent runtime.

This first version is a small Python CLI. You or your chosen agent prepare the text;
the CLI stores it, creates revisions, searches words, and checks metadata.
It does not call a model or access the network at runtime. Obsidian is an optional viewer.
Agent independence describes the file-based interface, not tested automatic integrations with every agent.
The CLI command is `second-brain`. The internal Python module remains `local_knowledge_wiki`; existing knowledge bundles need no migration.

## Prerequisites

**To read existing knowledge:** a file browser and any UTF-8 text or Markdown editor are enough.
Python, the CLI, an AI account, and Obsidian are not required just to read the files.

**To install and run the CLI:**

- **OS:** a local POSIX filesystem on macOS or Linux. Tested on macOS only; Linux is not yet validated.
  Windows is not supported because file access uses POSIX-specific APIs. WSL is not tested.
- **Python:** Python 3.11 or newer with the standard `venv` module. Tests used Python 3.14.6;
  the minimum supported version has not been tested separately.
- **Shell:** a terminal with a POSIX shell, such as bash or zsh, for the commands below.
- **Source files:** a local copy of this project, including `pyproject.toml`. Git is optional if you have an archive or copied source.
- **Install dependencies:** `pip` in the virtual environment. It installs PyYAML and build tools automatically.
  Package downloads normally need internet access; CLI operations do not.
- **Storage:** a writable local folder. `init` requires a new or empty target. Keep knowledge outside the code checkout and `.venv`.

Check your Python installation before you start:

```sh
python3 --version
python3 -m venv --help > /dev/null
```

If Python is older than 3.11, select a newer interpreter for `python3` in the commands below.
If `venv` is missing, install your OS distribution's Python venv support first.
No GPU, database, server, API key, Obsidian plugin, or required AI service is needed.
An agent is optional for writing the prepared text; you can write it yourself.

## Quick start

Run these commands from the project root (the directory containing `pyproject.toml`):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

The example uses fictional notes. The temporary directory remains after the shell exits,
so you can inspect the resulting files. The fixture is in Korean; search matches its exact word.

```sh
DEMO_DIR="$(mktemp -d "${TMPDIR:-/tmp}/second-brain.XXXXXX")"
second-brain init "$DEMO_DIR/wiki"
second-brain capture "$DEMO_DIR/wiki" examples/inputs/garden-note.txt \
  --id garden-note --actor human:demo --resource synthetic:garden-note
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v1.md --source garden-note --actor demo-agent/0.1 \
  --title '달빛 정원의 물주기' --stale-after '2030-01-01T00:00:00+00:00'
second-brain search "$DEMO_DIR/wiki" '물주기' --now '2026-10-27T00:00:00+00:00'
second-brain check "$DEMO_DIR/wiki" --now '2026-10-27T00:00:00+00:00'
```

The first check returns `invalid: []`, `warnings: []`, `stale: []`, and `concepts: 1`.
A new revision defaults to `draft` and `unverified`. After deliberately reviewing the
fictional body against its source, record that declaration:

```sh
second-brain review "$DEMO_DIR/wiki" garden --revision r000001 \
  --actor human:demo --evidence sources/garden-note/content.raw
second-brain show "$DEMO_DIR/wiki" garden --format json
```

This creates `r000002`, with the same body and a `human-reviewed` declaration, while
preserving `r000001`. It stays `draft`. The CLI does not check facts or authenticate `human:demo`.
Save a content edit; it starts `unverified` again:

```sh
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v2.md --source garden-note --actor demo-agent/0.1
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

All three revisions remain on disk. The index points to `r000003`, the content edit. Commands default to JSON.
Search and the read-only browsing commands also accept `--format text`.
Use `second-brain --help`, `second-brain curate --help`, or `second-brain review --help` for options.

## View your knowledge

### Without Obsidian

Open the **knowledge folder**, not the application source folder, in your file browser or editor.
Start with `index.md`: it links to the current revision of each concept. Open the linked Markdown file
to read its body and YAML metadata. Use an editor with Markdown preview if you prefer formatted text;
a plain text editor also works. This version has no built-in graphical viewer.

After the quick start above, read the current body, browse earlier revisions, compare changes,
and inspect the captured source record:

```sh
second-brain list "$DEMO_DIR/wiki" --format text
second-brain show "$DEMO_DIR/wiki" garden --format text
second-brain show "$DEMO_DIR/wiki" garden --revision r000001 --format json
second-brain history "$DEMO_DIR/wiki" garden --format text
second-brain diff "$DEMO_DIR/wiki" garden r000001 r000003 --format text
second-brain search "$DEMO_DIR/wiki" '물주기' --current-only --status draft \
  --freshness unknown --format text
second-brain search "$DEMO_DIR/wiki" '물주기' --status draft --freshness fresh \
  --now '2026-10-27T00:00:00+00:00' --format json
python -m json.tool "$DEMO_DIR/wiki/sources/garden-note/provenance.json"
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

`search` returns paths, metadata, and short body snippets. Use `show` for the full body.
`current: true` marks the indexed revision. Older revisions are kept for comparison.
`content.raw` preserves source bytes, so open it as text only when you know it is a text source;
it can also contain binary data. `provenance.json` records its origin, capture time, actor, and hash.
If you open another terminal, activate `.venv` again and set the path to your knowledge folder;
`DEMO_DIR` only exists in the shell where you set it.

### With Obsidian

1. First create and populate a **new knowledge folder** with the CLI. Do not run `init` on an existing, nonempty vault.
2. In Obsidian's vault switcher, choose **Open folder as vault**, then select that knowledge folder.
   For the quick start, it is the `wiki` folder under the path printed by `init`, not this project's checkout.
3. Open `index.md` and follow a current-version link to read a concept. Read the YAML in Source mode
   or inspect supported fields in Properties. Nested metadata can be read in Source mode.
4. Compare the revision files under `concepts/` and inspect source records under `sources/` as needed.
   Obsidian may not preview `.raw` or JSON files; use an external editor for them.
5. Use the terminal for `search`, `check`, and new revisions. Reading a note in Obsidian does not verify its content.

No community plugin, Sync subscription, or Publish service is required. Obsidian creates its own `.obsidian`
settings folder. Search, check, and revision traversal skip entries named exactly `.obsidian` or `.git`
at every depth, including symlinks with those names, without following or changing them. Other hidden
knowledge files and folders are scanned. Ordinary knowledge symlinks are still rejected.
To preserve revision history, prepare edits in a separate file and run `curate`, rather than editing an old revision in place.

These instructions follow the [official Obsidian folder-as-vault guide](https://help.obsidian.md/vault).
The graphical workflow has not been independently tested for this project.

## How it works

1. **Capture:** Copy an explicitly selected source file without changing its bytes.
2. **Prepare:** Read that source and write a Markdown body, yourself or with your chosen agent.
3. **Curate:** Store the prepared body as a new concept revision with source references.
4. **Recall:** Search notes and inspect their current-version, review, and freshness context.
5. **Check:** Report metadata errors, local-link warnings, and stale notes separately.
6. **Review:** Deliberately compare the current body with evidence, then record the declared reviewer and reference.

There is no background learning loop or built-in LLM synthesis.
`curate` stores prepared text; it does not summarize or verify it.

| Command | Purpose |
| --- | --- |
| `init BUNDLE` | Create an index in a new or empty directory. Refuse nonempty targets. |
| `capture BUNDLE FILE --id ID --actor ACTOR --resource ORIGIN` | Preserve source bytes, origin, actor, capture time, and SHA-256. Refuse reused source IDs. |
| `curate BUNDLE ID --body FILE --source SOURCE_ID --actor ACTOR` | Store a prepared UTF-8 body as a new revision. Repeat `--source` for multiple sources. |
| `review BUNDLE ID --revision rNNNNNN --actor ACTOR --evidence RESOURCE` | Append a declared review in a new revision of the current body. |
| `search BUNDLE QUERY` | Search titles and bodies across all concept revisions. |
| `list BUNDLE` | List all CLI revision summaries, sorted by path. |
| `show BUNDLE ID [--revision rNNNNNN]` | Read the indexed current revision, or an explicit revision. |
| `history BUNDLE ID` | List revision summaries from oldest to newest. |
| `diff BUNDLE ID BEFORE AFTER` | Compare two explicit revisions, including metadata and body. |
| `check BUNDLE` | Check the supported metadata subset and report links and freshness. |

IDs are 1–64 lowercase ASCII letters, digits, or hyphens, starting with a letter or digit.
`curate` also accepts `--type`, `--title`, `--status`, and `--stale-after`.
`--actor` is a declared identity, not authentication. Only an explicit `review` adds `verified`; format validation never does.
Relative body links resolve from the final revision file, not the prepared input file.

```text
wiki/
  index.md
  sources/garden-note/
    content.raw
    provenance.json
  concepts/garden/
    r000001.md
    r000002.md
    r000003.md
```

Sources retain their encoding, BOM, and line endings. Even Markdown sources are stored as
`.raw`, separate from concept documents. There is no source-text search, PDF extraction,
or encoding detection. Prepared bodies and concept documents must be UTF-8.

`list`, `show`, `history`, and `diff` are read-only. They use CLI files at
`concepts/ID/r000001.md` through `r999999.md`. Revision arguments must be exactly `rNNNNNN`;
IDs follow the same rules as `curate`. `show` never guesses the current revision from the highest number.
If the current index is unavailable, use `--revision`. Summaries include the current marker, lifecycle,
trust, freshness, and metadata errors. `show` also includes the full body and metadata.
`diff` emits a unified diff of the complete stored Markdown, including metadata, with three context lines;
equal revisions produce an empty JSON `diff` or `No differences.` in text mode.
Imported generic OKF notes remain readable through search/check and a text editor; these commands do not
infer revision history for them. Missing concepts/revisions and unsafe paths return exit `2`.
Malformed note metadata is reported in `metadata_errors` (text mode labels each error); browsing still
returns available content. Invalid UTF-8 is reported with an empty body. Diff refuses invalid notes.
Non-string YAML mapping keys are converted to strings in output only. Stored notes are unchanged.
Mappings with colliding converted keys or cyclic values return a deliberate error instead of losing data.
Read-command operational errors are a JSON `{"error": "..."}` object on stderr in JSON mode, or a
`second-brain:` message in text mode. Argument syntax errors use argparse's text diagnostic.

`review` requires the exact indexed current revision and refuses historical targets under the write lock.
Actors must be `human:ID`, `process:ID`, or `PRODUCER/VERSION`, with nonempty components and no
whitespace, controls, colon, slash or backslash inside a component. These are declarations.
The CLI records its observed offset-aware UTC time; it accepts no historical review timestamp.
Evidence must be an absolute HTTP(S) URL with a host (no credentials, invalid ports/escapes or whitespace),
or an existing nonempty regular artifact at a literal bundle-root path, optionally starting with `/`.
Local spaces are allowed, but query/fragment syntax, traversal, backslashes, application directories
and symlinks are refused. Unsupported URL schemes are refused. URLs are never fetched and evidence
is never executed. References are declarations, not proof of truth.

The new event uses standard OKF `by`/`at` and project extensions `x-second-brain-target`
(`resource` and SHA-256 of the complete target file) and `x-second-brain-evidence`
(`resource`, plus SHA-256 for local evidence). Digests identify observed bytes; they do not authenticate
reviewers. The original file stays byte-for-byte intact. The new body and metadata values, including
unknown YAML keys and original generation records, are preserved; new YAML formatting may differ.
Existing mapping/list review events are retained in a list. Status is unchanged, and a later `curate`
does not inherit reviews. See the bilingual [review contract](docs/review-contract.md) for details and failure limits.

## Search and trust signals

Search uses exact Unicode `\w+` tokens after `casefold`. All query words must match.
Scores sum occurrences of distinct query words; ties sort by path. There is no semantic,
substring, or morphological search. Older revisions remain searchable by default; existing JSON keys
and scoring are retained. `snippet` adds the first 160 Unicode characters of the body after whitespace
is collapsed (the final character is `…` when truncated). `title` is also included.

Use `--current-only` to require an indexed current revision; unknown current status is excluded.
`--status draft|stable|deprecated` filters lifecycle status and excludes invalid metadata. An omitted
status on an otherwise valid OKF note means `stable`, as before. `--freshness fresh|stale|unknown`
uses only `stale_after`: fresh means a valid deadline later than `--now`, stale means that deadline
has been reached, and unknown means an absent or invalid deadline, including one without a UTC offset.
Unrelated metadata errors remain visible but do not change freshness. Filters combine with AND and
apply to individual revisions; a matching older revision is never substituted for the current one.
Use `--now` for reproducible evaluation and `--format text` for readable Unicode output.

Each result includes `current`, `status`, `trust`, `stale`, generation and verification records,
and metadata errors. `current: null` means the CLI cannot identify a current-version index.
`stale: null` means no usable expiry date is available. Review tiers interpret stored records;
they do not prove that a reviewer checked the facts or that their identity is authentic.

`check` scans Markdown files outside `.obsidian` and `.git` and recognizes reserved `index.md` and `log.md` files.
Broken links and stale documents are separate from metadata errors:

- Exit `0`: no metadata errors; link warnings or stale notes may still be present.
- Exit `1`: metadata errors.
- Exit `2`: I/O failure, unsafe operation, or invalid arguments.

This is not a complete OKF validator or a factual-verification service.
See the exact [OKF subset](docs/okf-subset.md) and [architecture and recovery limits](docs/architecture.md).
These detailed documents are currently in Korean.

## Agent workflow and scope

Start with the [portable agent guide and task template](docs/agent-kit.md), then give your
chosen agent the [English workflow](workflows/AGENT-WORKFLOW.md) and
[body template](templates/concept-body.md). Each has a Korean counterpart.
The older [synthetic bundle](examples/bundle/index.md) remains in Korean.
Keep instructions and templates outside the knowledge bundle.

Run a separate synthetic reuse demo from this checkout with the environment active.
The output goes under the quick start's temporary `DEMO_DIR`, separate from its `wiki`:

```sh
python examples/knowledge_reuse.py --output "$DEMO_DIR/reuse-demo"
second-brain show "$DEMO_DIR/reuse-demo/wiki" lantern --format text
second-brain history "$DEMO_DIR/reuse-demo/wiki" lantern --format text
```

This asserts an empty lookup, source capture, a prepared note, later-task recall/reuse,
revised source/content, current selection, preserved bytes and history/comparison.
Inspect `reuse-before.json`, `reuse-after.json`, `transcript.json` and `summary.json` under
`reuse-demo`. The [guide](docs/agent-kit.md#run-the-synthetic-reuse-demo) explains every artifact.
The demo uses prewritten English synthetic notes and deterministic CLI orchestration,
not LLM synthesis or a factual verifier. Its `process:synthetic-demo` review is a demo
declaration, not authenticated or human review; the later edit is `unverified`.
Real Claude, Codex and Grok integrations were not tested. No model, vendor, account or
API key is required. The CLI runs offline; external agents follow their own policies
and need separate authorization for external data transfer. Examples and docs are
source-checkout resources, not a published standalone package.

CLI writes use an exclusive lock and refuse to overwrite existing sources or revisions.
Only the marked current-version block in the root index is managed; surrounding human text stays intact.
Editors do not honor this lock. Do not edit concurrently with a write command.
Crash leftovers are preserved for manual inspection, not automatically deleted or repaired.

There is no web UI, daemon, vector database, cloud backend, MCP server, computation execution,
or attestation in this version. A license has not been selected; no reuse license is granted by this repository.
No PyPI package release is available. Install from the source checkout.

## Development checks

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests examples
python -m pip check
```

Run `python tests/verify_quickstart.py` to execute the shell blocks of both READMEs in
separate temporary project copies and fresh virtual environments.
These source workflows intentionally use the checkout examples. The verification checks
installation, source-byte preservation, revision history, the documented viewing commands,
and the separate reuse demo outputs.
Obsidian GUI steps are documented from official help, not independently tested.

Run `python scripts/verify_wheel.py` from the checkout to build the project wheel with
`pip wheel`, install it and its dependencies into a fresh venv without system site
packages, and smoke-test it outside the checkout with `PYTHONPATH` cleared. It proves
the package imports from that venv and exercises init, capture, curate, search, check,
review and all four read commands, including preservation of source and revision bytes.
Inputs are synthetic temporary files independent of the checkout examples; HOME and
pip cache writes stay in the temporary directory. Installation can download build tools
and dependencies; the CLI makes no runtime API calls. Temporary smoke artifacts are
removed when the check exits. This does not publish a package.

[CI](.github/workflows/ci.yml) is configured for pull requests and pushes to `main`,
with `macos-latest` and `ubuntu-latest`, each on Python 3.11 and 3.14. Each of the four
jobs runs the full unittest suite and wheel smoke check; only macOS/Python 3.14 runs
both README source workflows. The workflow has read-only contents permission and
uses pinned official actions without persisted checkout credentials. There is no
schedule or automatic publishing.

Local validation on macOS with Python 3.14.6 passed all 50 unit tests, the clean wheel
smoke check, both README workflows, compilation and `pip check`. Hosted Actions jobs
have not yet been observed. Linux and minimum-Python (3.11) validation remain pending;
the configured matrix alone is not evidence of support.
