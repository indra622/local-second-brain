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
A new revision defaults to `draft` and `unverified`. Save another revision:

```sh
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v2.md --source garden-note --actor demo-agent/0.1
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

Both revisions remain on disk. The index points to the second one. Commands return JSON.
Use `second-brain --help` or `second-brain curate --help` for options.

## View your knowledge

### Without Obsidian

Open the **knowledge folder**, not the application source folder, in your file browser or editor.
Start with `index.md`: it links to the current revision of each concept. Open the linked Markdown file
to read its body and YAML metadata. Use an editor with Markdown preview if you prefer formatted text;
a plain text editor also works. This version has no built-in graphical viewer.

After the quick start above, these commands show the current links, the second note revision,
and the captured source record:

```sh
cat "$DEMO_DIR/wiki/index.md"
cat "$DEMO_DIR/wiki/concepts/garden/r000002.md"
python -m json.tool "$DEMO_DIR/wiki/sources/garden-note/provenance.json"
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

`search` returns paths and metadata, not the full note text. Read the returned path in your editor.
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
settings folder. It is not a knowledge source. The current checker does not exclude application folders:
additional Markdown files in plugin/config folders can be scanned, so start without community plugins.
To preserve revision history, prepare edits in a separate file and run `curate`, rather than editing an old revision in place.

These instructions follow the [official Obsidian folder-as-vault guide](https://help.obsidian.md/vault).
The graphical workflow has not been independently tested for this project.

## How it works

1. **Capture:** Copy an explicitly selected source file without changing its bytes.
2. **Prepare:** Read that source and write a Markdown body, yourself or with your chosen agent.
3. **Curate:** Store the prepared body as a new concept revision with source references.
4. **Recall:** Search notes and inspect their current-version, review, and freshness context.
5. **Check:** Report metadata errors, local-link warnings, and stale notes separately.

There is no background learning loop or built-in LLM synthesis.
`curate` stores prepared text; it does not summarize or verify it.

| Command | Purpose |
| --- | --- |
| `init BUNDLE` | Create an index in a new or empty directory. Refuse nonempty targets. |
| `capture BUNDLE FILE --id ID --actor ACTOR --resource ORIGIN` | Preserve source bytes, origin, actor, capture time, and SHA-256. Refuse reused source IDs. |
| `curate BUNDLE ID --body FILE --source SOURCE_ID --actor ACTOR` | Store a prepared UTF-8 body as a new revision. Repeat `--source` for multiple sources. |
| `search BUNDLE QUERY` | Search titles and bodies across all concept revisions. |
| `check BUNDLE` | Check the supported metadata subset and report links and freshness. |

IDs are 1–64 lowercase ASCII letters, digits, or hyphens, starting with a letter or digit.
`curate` also accepts `--type`, `--title`, `--status`, and `--stale-after`.
`--actor` is a declared identity, not authentication. The CLI never adds `verified` automatically.
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
```

Sources retain their encoding, BOM, and line endings. Even Markdown sources are stored as
`.raw`, separate from concept documents. There is no source-text search, PDF extraction,
or encoding detection. Prepared bodies and concept documents must be UTF-8.

## Search and trust signals

Search uses exact Unicode `\w+` tokens after `casefold`. All query words must match.
Scores sum occurrences of distinct query words; ties sort by path. There is no semantic,
substring, or morphological search. Older revisions remain searchable.

Each result includes `current`, `status`, `trust`, `stale`, generation and verification records,
and metadata errors. `current: null` means the CLI cannot identify a current-version index.
`stale: null` means no usable expiry date is available. Review tiers interpret stored records;
they do not prove that a reviewer checked the facts or that their identity is authentic.

`check` scans Markdown files and recognizes reserved `index.md` and `log.md` files.
Broken links and stale documents are separate from metadata errors:

- Exit `0`: no metadata errors; link warnings or stale notes may still be present.
- Exit `1`: metadata errors.
- Exit `2`: I/O failure, unsafe operation, or invalid arguments.

This is not a complete OKF validator or a factual-verification service.
See the exact [OKF subset](docs/okf-subset.md) and [architecture and recovery limits](docs/architecture.md).
These detailed documents are currently in Korean.

## Agent workflow and scope

Give your chosen agent the [portable workflow](workflows/AGENT-WORKFLOW.md), use the
[body template](templates/concept-body.md), or inspect the [synthetic bundle](examples/bundle/index.md).
These supporting documents are currently in Korean. Keep instructions and templates outside the knowledge bundle.

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
python -m compileall -q src tests
python -m pip check
```

Run `python tests/verify_quickstart.py` to execute the shell blocks of both READMEs in
separate temporary project copies and fresh virtual environments.
The verification checks installation, source-byte preservation, revision history, and the documented viewing commands.
Obsidian GUI steps are documented from official help, not independently tested.
