# Human navigation without a second current store

**English** | [한국어](navigation.ko.md)

The CLI's index.md block between `<!-- lkw:current:start -->` and
`<!-- lkw:current:end -->` is the sole authoritative current selection. Never change its
markers, entries or line endings by hand. CLI writes manage that block and preserve
surrounding content. Frozen concepts/ID/rNNNNNN.md and captured sources are never edited.

For authorized setup or a requested save/revision, the agent may maintain the separate
`lsb:knowledge-nav` fragment from [landing-fragment.md](landing-fragment.md) **outside**
the CLI block in root index.md. This is a human reading aid, not another current registry.
Revision links are labeled snapshots as of the inspected managed block. Always resolve
current from that block before use. Other CLI/external changes can stale this aid; on a
read-only question report staleness and use actual current, never refresh it silently.

## Plan, do, verify

1. Require actual navigation-write authority and an exclusive no-concurrent-external-edit
   window. General read permission or answer-only intent is insufficient. If unavailable,
   prepare a proposed fragment in the permitted output directory; do not touch the bundle.
2. Read index bytes and managed selection **after** any CLI write. Identify the one owned
   fragment if present; preserve all user text/frontmatter/other regions. Missing fragment
   may be inserted only where explicitly authorized outside managed markers. Duplicated,
   malformed or ambiguous markers mean stop/draft, not repair/replace the whole index.
3. Fill human titles and exact original/previous/justified-related links. Headings can be
   customized; do not impose categories, force a link, create folder migrations or invent
   aliases. Current knowledge remains in its immutable CLI revisions, not copied into landing.
4. Before writing, reread and require the complete index bytes to equal the plan's base.
   If different, discard that proposed update and reassess; do not overwrite the new index.
   Replace only the owned fragment (or authorized insertion). Keep bytes outside it exact,
   including CLI marker bytes. Do not normalize the entire document's newlines/encoding.
5. Read back: parse the unchanged CLI managed entries, compare all unrelated user bytes,
   follow each real relative file, and use show/history/diff as appropriate to confirm
   current/old/source meanings. Broken links or uncertain provenance are not a success.

These are agent/file-tool steps, not a new CLI navigation command. CLI locks coordinate
CLI writers, not this external edit. Rechecking does not make concurrent editors safe or
supply a transaction/journal; the exclusive work window is required. Do not clear locks,
change intents or infer recovery from a landing page. The operational workflow remains
in force. Plain Markdown/text browsing works without Obsidian; opening a bundle in that
optional viewer neither imports all vaults nor authorizes bulk migration.
