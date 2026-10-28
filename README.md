# Local Second Brain

**English** | [한국어](README.ko.md)

Keep source files and reusable notes in a local folder. Local Second Brain is a small
Python command-line tool for people and agents who need to find a note later, see its
source, and keep earlier versions when it changes.

You or your agent write the note. The CLI copies sources without changing their bytes,
stores Markdown revisions, searches exact words, and checks metadata. It does not call
a model or access the network at runtime. You can read the files in any text editor;
Obsidian is an optional viewer.

Early alpha. Use Python 3.11+ with `venv`, a POSIX shell, and a writable local filesystem
on macOS or Linux. CI covers macOS and Ubuntu with Python 3.11 and 3.14. Other Linux
environments and WSL are not separately validated; Windows is unsupported.

## Quick start

Get the source with Git, then enter the checkout. If you downloaded an archive instead,
extract it and open a terminal in the directory containing `pyproject.toml`.
There is no PyPI release. Examples and guides come with this source checkout.

```text
git clone https://github.com/indra622/local-second-brain.git
cd local-second-brain
```

Check Python, create an isolated environment, and install. Installation normally needs
internet access to download PyYAML and build tools. No AI account or API key is required.
If Python is older than 3.11 or lacks `venv`, install a suitable interpreter first.

```sh
python3 --version
python3 -m venv --help > /dev/null
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

This example turns a fictional garden source into a saved watering note, then finds it
with the exact Korean word `물주기` (watering). **Capture** means copy the selected source
and record its origin. **Curate** means save a note you have already written, linked to
that source. The example uses prepared files; neither command generates text.

Keep the knowledge folder outside the checkout. The following temporary folder remains
on disk so you can inspect it. Save the `DEMO_DIR=...` line printed below. It is the
parent directory; `init` prints the separate knowledge-folder path ending in `/wiki`.

```sh
DEMO_DIR="$(mktemp -d "${TMPDIR:-/tmp}/second-brain.XXXXXX")"
printf 'DEMO_DIR=%s\n' "$DEMO_DIR"
second-brain init "$DEMO_DIR/wiki"
second-brain capture "$DEMO_DIR/wiki" examples/inputs/garden-note.txt \
  --id garden-note --actor human:demo --resource synthetic:garden-note
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v1.md --source garden-note --actor demo-agent/0.1 \
  --title '달빛 정원의 물주기' --stale-after '2030-01-01T00:00:00+00:00'
second-brain search "$DEMO_DIR/wiki" '물주기' --now '2026-10-27T00:00:00+00:00'
second-brain check "$DEMO_DIR/wiki" --now '2026-10-27T00:00:00+00:00'
```
Read the saved note:

```sh
second-brain show "$DEMO_DIR/wiki" garden --format text
```

Search finds `concepts/garden/r000001.md` with `current: true`, `draft` status and
`unverified` trust. The first `check` reports `invalid: []`, `warnings: []`,
`stale: []`, and `concepts: 1`. These are metadata results, not a fact check.
Open the knowledge folder's `index.md` to follow its link to the note.

## Continue

- [Review, revise, and recall](docs/getting-started.md): continue this example, keep three revisions, and run a separate synthetic reuse task. Includes optional Obsidian instructions.
- [Use your own agent](docs/agent-kit.md): prepare sourced notes and reuse them in later work. The file interface does not require a particular agent or automatic integration.
- [Public-source Codex validation](docs/field-validation.md) (Korean): an actual agent-written note and follow-up task, with search misses and a GUI access limit. This is one manual run, not an integration test for every agent.
- [Command and support reference](docs/reference.md): exact search rules, review declarations, safety and recovery limits. [Developer checks](docs/development.md) describes tests and CI.

Review identities are declarations, not authenticated identities. Search is based on
exact words, not meaning. Keep original revisions intact: prepare changes in a separate
file and save them with `curate`. Detailed contracts are in the reference.

## License and attribution

This project's original implementation and documentation are licensed under the
[MIT License](LICENSE). Copyright (c) 2026 indra622.

The implementation draws on LLM Wiki workflow concepts and the
[Open Knowledge Format (OKF) specification](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).
Those concepts and third-party materials remain attributed to their respective authors.
Third-party code, documentation, and captured source materials retain their own licenses
and terms; this project's MIT license does not relicense them.
