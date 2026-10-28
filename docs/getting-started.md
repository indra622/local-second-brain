# Next steps: review, revise, and recall

**English** | [한국어](getting-started.ko.md)

Continue in the same shell after the [README quick start](../README.md#quick-start).
In a new terminal, return to the checkout and activate the virtual environment.
Restore the `DEMO_DIR=...` line saved from the README. This is the parent directory,
not the knowledge-folder path ending in `/wiki`; the commands below add `/wiki`.

## Review and revise

The saved note says to send the report on Friday. Compare it with the captured
fictional memo, then record that you reviewed it. It is still a draft; saving alone
does not record a review (`status: draft`, `trust: unverified`). The README's `check`
only checks metadata structure and links, not whether the rule is true.

```sh
second-brain review "$DEMO_DIR/wiki" report-rules --revision r000001 \
  --actor human:demo --evidence sources/report-memo-1/content.raw
second-brain show "$DEMO_DIR/wiki" report-rules --format json
```

This creates `r000002`, with the same body and a `human-reviewed` declaration, while
preserving `r000001`. It stays `draft`. The CLI does not check facts or authenticate `human:demo`.
Now the fictional team moves the report to Thursday. Capture the prepared update
and save the revised note with a link to that new source. The edited note has no
review declaration (`unverified`), even though its predecessor was reviewed:

```sh
second-brain capture "$DEMO_DIR/wiki" examples/inputs/report-memo-2.txt \
  --id report-memo-2 --actor human:demo --resource synthetic:report-memo-2
second-brain curate "$DEMO_DIR/wiki" report-rules \
  --body examples/inputs/report-v2.md --source report-memo-2 --actor prepared-fixture/1
second-brain search "$DEMO_DIR/wiki" 'report'
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
second-brain show "$DEMO_DIR/wiki" report-rules --format text
second-brain show "$DEMO_DIR/wiki" report-rules --revision r000001 --format json
second-brain history "$DEMO_DIR/wiki" report-rules --format text
second-brain diff "$DEMO_DIR/wiki" report-rules r000001 r000003 --format text
second-brain search "$DEMO_DIR/wiki" 'report' --current-only --status draft \
  --freshness unknown --format text
second-brain search "$DEMO_DIR/wiki" 'report' --status draft --freshness fresh \
  --now '2026-10-27T00:00:00+00:00' --format json
python -m json.tool "$DEMO_DIR/wiki/sources/report-memo-1/provenance.json"
second-brain search "$DEMO_DIR/wiki" 'report'
second-brain check "$DEMO_DIR/wiki"
```

`search` returns paths, metadata, and short body snippets. Use `show` for the full body.
`current: true` marks the indexed revision. Older revisions are kept for comparison.
The third revision has no recheck date, so its `freshness` is `unknown`. The first two
match `fresh` because the specified date has not passed. These labels describe the
recheck date, not a review or factual accuracy. All three revisions remain `draft`.
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

## Synthetic reuse example

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
`reuse-demo`. The [guide](agent-kit.md#run-the-synthetic-reuse-demo) explains every artifact.
The demo uses prewritten English synthetic notes and deterministic CLI orchestration,
not LLM synthesis or a factual verifier. Its `process:synthetic-demo` review is a demo
declaration, not authenticated or human review; the later edit is `unverified`.
Automatic Claude, Codex and Grok integrations were not tested. A separate
[public-source Codex run](field-validation.md) records manual CLI use and its limits. No model, vendor, account or
API key is required. The CLI runs offline; external agents follow their own policies
and need separate authorization for external data transfer. Examples and docs are
source-checkout resources, not a published standalone package.
