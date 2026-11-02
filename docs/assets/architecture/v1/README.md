# Architecture illustrations v1

These static README illustrations preserve the six roles and eight directed relations of the approved Korean Archify candidate. They show commands and dependencies, not autonomous host integration. The compact canvas moves detailed explanations into the READMEs. English native-viewer placement is adjusted to avoid a routed crossing; the static canvas uses the same two-row layout in both languages.

- [Korean SVG](local-second-brain.ko.svg) and [PNG](local-second-brain.ko.png)
- [English SVG](local-second-brain.en.svg) and [PNG](local-second-brain.en.png)
- [Approved Korean semantic source](approved.ko.json), copied without changes
- [Translated English semantic source](approved.en.json), with the same role IDs, connections, evidence and pinned repository revision

Architecture evidence is pinned to `0b40e8e58f5baa8de9d25d8f67de4b01379fe8bc`. The approved candidate SHA-256 is `1aceba6439dfd9ebffb973f6492f2ce4327b634e14dac4f280bb63b68d85291b`. Source paths and line ranges refer to that revision. The sources' relative `meta.output` paths are optional Archify viewer destinations, not committed artifacts.

## Reading boundaries

The external agent prepares Markdown outside the knowledge bundle and remains responsible for understanding and reasoning. The kit and user-owned profile are explicitly activated documents and preferences outside that bundle. They are not a CLI `--profile` option, an enforced sandbox or automatic memory. Agent-provider transmission requires separate authorization.

The CLI manages current links; authorized agent file tools maintain the separate human navigation area. The optional viewer reads files and is not a shipped note-editing GUI. Arrows describe invocations and dependencies, not autonomous host integration. No vector database, MCP server or native model service is implied.

Write locks, request replay and current-revision comparisons protect bounded operations. They are not full transactions, atomic crash recovery or authenticated human review. See [implementation architecture](../../../architecture.md), [English reference](../../../reference.md) and [Korean reference](../../../reference.ko.md) for the existing contracts and limits.

## Regenerate

From the repository root, using Python 3.11 or newer:

```sh
python3 docs/assets/architecture/v1/render.py
```

This dependency-free static adapter reads the pinned Archify sources and emits only SVG. Its fixed two-row layout and compact translated labels are in `render.py`. Every relationship retains its source ID, direction and dashed/direct-read distinction. SVG has an explicit white background for consistent contrast in light and dark README themes. It uses system fonts, without scripts, remote resources or embedded fonts.

For PNG fallback, with an **existing** Playwright and Chrome installation available to Node:

```sh
node docs/assets/architecture/v1/render-png.cjs
```

`NODE_PATH` may point to an existing Playwright installation. This optional export tool is not a project dependency or an installation step. It renders the SVG at 930 × 540 CSS pixels with scale factor 2, producing 1860 × 1080 PNGs. Font rasterization can vary across operating systems; SVG generation is deterministic. No viewer chrome, HTML or runtime is needed to display either image.

For native Archify validation/viewer generation, use an existing archify installation, replacing `ARCHIFY` with its CLI entry point and `OUTSIDE_REPO` with a disposable output directory:

```sh
node "$ARCHIFY" finalize architecture docs/assets/architecture/v1/approved.ko.json "$OUTSIDE_REPO/ko.html" --repo-root . --quality showcase --json
node "$ARCHIFY" finalize architecture docs/assets/architecture/v1/approved.en.json "$OUTSIDE_REPO/en.html" --repo-root . --quality showcase --json
```

Native Archify gates validate the semantic sources and generated viewers. They do not validate the separate compact static adapter. Inspect both static exports at 830px displayed width after layout or translation changes, including text fit, arrowheads and label contrast. Do not commit the viewer HTML or local receipts.
