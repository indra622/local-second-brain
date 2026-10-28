# Local Second Brain

**English** | [한국어](README.ko.md)

Local Second Brain is a local file-based notebook for agent-assisted work that keeps
reusable notes tied to their source files and earlier versions.

## Pick up the reasoning in your next session

You work through a project question with an agent, compare sources, and reach a useful
decision. Weeks later, another task needs that reasoning. A saved conversation holds the
exchange, but you still need to identify the conclusion, its basis, and whether it still
applies. A short summary is easier to reuse, but can leave those connections behind.
Rebuilding that context costs time and makes it easy to reuse an outdated assumption.

This project gives that work a place outside the conversation. You select local source
files; you or your chosen agent prepare a note with the decision, evidence, and limits.
The Python CLI stores them together under an explicit convention for sources, revisions,
and the current note. In a later session, you can find the note, read its basis, and
choose what to reuse or recheck.

## What you keep when a note changes

- **The basis behind the summary.** Capture preserves the selected source bytes and
  records their origin, capture time, declared actor, and SHA-256 hash. Prepared notes
  link back to those files. You can revisit what the note was based on, even if the
  original document later changes.
- **A current answer with its history.** Each saved revision is a new Markdown file;
  earlier revisions are not overwritten. An index selects the current one, while
  history and diff let you inspect past reasoning and what changed. Later work can
  use the current note without erasing how you got there.
- **Context for deciding what to recheck.** Results show current-version status,
  declared reviews, and freshness based on an optional deadline. A new content revision
  does not inherit the old review. These signals help you decide where to spend review
  effort; they do not verify facts or authenticate reviewers.
- **Files you can keep using.** Notes are ordinary Markdown, provenance is JSON, and
  captured sources retain their bytes. You can read and keep them without an AI account,
  model backend, or this CLI. The workflow and body template give a person or a chosen
  agent the same preparation steps while the CLI keeps storage consistent.

You could maintain these links and versions in plain notes yourself. The value here is
making that convention explicit and applying it with commands, so each new session does
not have to invent its own way to preserve sources and distinguish current from past work.

## Example: revisit a project's archive naming rule

This is an illustrative workflow for a recurring project decision:

1. **Before:** An agent helped you decide how to name exported archives. When you later
   build a migration checklist, you find a summary saying “use the new naming rule,”
   but still have to recover which requirements it used and whether the rule changed.
2. **Preserve the decision:** Select the local requirements and sample filenames,
   capture them, and ask your agent to write an `archive naming` note: why exports use
   a UTC date, as in `metrics-2026-10-28.zip`, and which exceptions apply. Save it with
   source links. Compare it with the evidence yourself if needed, then record a review
   declaration and an optional recheck deadline.
3. **After:** In a later session, direct the agent to search for the exact words
   `archive naming`, read the current note and its sources, and use it to draft the
   checklist. If requirements change, capture the changed file under a new source ID
   and save a new note revision. The index points to that revision; history and diff
   still show the earlier rule and why it was chosen, as recorded in the note.

You or the agent perform the reading and reasoning. The CLI preserves and retrieves
that work. A [manual Codex run](docs/field-validation.md) exercised source capture,
agent-written notes, later reuse, and revision comparison once; it is not evidence of
automatic memory or an integration with every agent.

## When to use it

Use it for project decisions or research findings you expect to revisit across sessions,
when you can select the local evidence and want both a reusable note and a path back to
its basis. It fits people willing to choose what to save and direct a person or agent
to prepare and recall it.

For a broad note app, instant AI chat, or an automatic collector of everything you read,
choose a tool built for that job. This CLI has exact-word search, not semantic search;
it has no model calls, GUI, or MCP server, and implements only part of OKF. Obsidian can
be an optional viewer. The CLI does not use the network at runtime; external agents
have their own network and data policies.

## For agents

To have an agent install and verify the tool, give it this prompt. For manual setup,
follow [Quick start](#quick-start) below.

```text
Install and verify Local Second Brain from https://github.com/indra622/local-second-brain.git.
Clone into a new working folder, or inspect and reuse an existing checkout without
overwriting user changes. Read its README and supported requirements first.
Create a project-local .venv and use the documented source install: python -m pip install -e .
With that environment active, verify second-brain --help and run the README synthetic
quickstart from the checkout, using a separate new temporary knowledge folder.
Report the checkout, CLI executable, and demo folder paths, commands, and results.
Keep this task to installation and the synthetic demo: do not scan personal vaults,
upload data, change global configuration, or pipe remote installers into a shell.
Installation does not provide automatic memory or model integration.
```

For later work with your own notes, use the [portable agent kit](docs/agent-kit.md)
and its [workflow](workflows/AGENT-WORKFLOW.md).

## Quick start

Early alpha. Use Python 3.11+ with `venv`, a POSIX shell, and a writable local filesystem
on macOS or Linux. CI covers macOS and Ubuntu with Python 3.11 and 3.14. Other Linux
environments and WSL are not separately validated; Windows is unsupported.

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

Keep original revisions intact: prepare changes in a separate file and save them with
`curate`. Detailed contracts are in the reference.

## License and attribution

This project's original implementation and documentation are licensed under the
[MIT License](LICENSE). Copyright (c) 2026 indra622.

The implementation draws on LLM Wiki workflow concepts and the
[Open Knowledge Format (OKF) specification](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).
Those concepts and third-party materials remain attributed to their respective authors.
Third-party code, documentation, and captured source materials retain their own licenses
and terms; this project's MIT license does not relicense them.
