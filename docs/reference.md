# Commands and support reference

**English** | [한국어](reference.ko.md)

## Prerequisites

**To read existing knowledge:** a file browser and any UTF-8 text or Markdown editor are enough.
Python, the CLI, an AI account, and Obsidian are not required just to read the files.

**To install and run the CLI:**

- **OS:** a local POSIX filesystem on macOS or Linux. CI-tested on hosted macOS and Ubuntu runners; other Linux environments are not separately validated.
  Windows is not supported because file access uses POSIX-specific APIs. WSL is not tested.
- **Python:** Python 3.11 or newer with the standard `venv` module. CI covers Python 3.11 and 3.14; local validation used Python 3.14.6.
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
does not inherit reviews. See the bilingual [review contract](review-contract.md) for details and failure limits.

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
See the exact [OKF subset](okf-subset.md) and [architecture and recovery limits](architecture.md).
These detailed documents are currently in Korean.

## Agent and storage limits

Start with the [portable agent guide and task template](agent-kit.md), then give your
chosen agent the [English workflow](../workflows/AGENT-WORKFLOW.md) and
[body template](../templates/concept-body.md). Each has a Korean counterpart.
The older [synthetic bundle](../examples/bundle/index.md) remains in Korean.
Keep instructions and templates outside the knowledge bundle.

CLI writes use an exclusive lock and refuse to overwrite existing sources or revisions.
Only the marked current-version block in the root index is managed; surrounding human text stays intact.
Editors do not honor this lock. Do not edit concurrently with a write command.
Crash leftovers are preserved for manual inspection, not automatically deleted or repaired.

There is no web UI, daemon, vector database, cloud backend, MCP server, computation execution,
or attestation in this version.
No PyPI package release is available. Install from the source checkout.

## File interface

The internal Python module remains `local_knowledge_wiki`; existing bundles need no migration.
