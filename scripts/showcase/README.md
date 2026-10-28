# Reproduce the showcase

These development scripts do not change the CLI runtime. All inputs in `fixtures/` are synthetic, prepared text. No model writes them. Use the project's documented local Python installation; the only Python dependency is the existing PyYAML dependency. Rendering requires existing `magick`. Browser QA uses an existing Playwright installation and Chrome; nothing installs globally.

From the checkout, use an output directory outside it:

```sh
SHOWCASE_LOGS="$(mktemp -d "${TMPDIR:-/tmp}/showcase-evidence.XXXXXX")"
.venv/bin/python scripts/showcase/generate.py --logs "$SHOWCASE_LOGS/raw"
.venv/bin/python scripts/showcase/render.py --frames "$SHOWCASE_LOGS/frames"
```

The generator invokes actual init, capture, curate, search, show, history, diff and check commands in a fresh temporary bundle. It records full argv/stdout/stderr externally, hashes the complete first revision and source immediately after the first save, and asserts that both remain byte-identical after the update. It also asserts exact fixture source/body bytes, index selection, current search and a clean check. Temporary bundles are removed on exit. Captures declare `process:showcase`; the notes declare `prepared-fixture/1`, remain drafts and have no review records.

`site/data/sample.json` contains actual CLI results, copied source text and hashes. Full replay commands and unabridged stdout are in `transcript.txt`. The public display replaces the temporary bundle path with `sample/wiki` and the fixture directory with `fixtures`; these are display aliases. Timestamps remain actual capture timestamps, so a new run changes hashes and diffs. Freshness is evaluated at an explicit fixed sample instant. This is reproducible behavior, not byte-identical timestamp output across runs.

The renderer selects actual output lines programmatically: save result, current search context, note context/body without the verbose Metadata line, and file headers plus Friday/Thursday changed lines. Every selected line must occur verbatim in the captured stdout. Editorial captions sit outside the excerpt. The full transcript retains metadata and commands. `replay-selection.json` records the selected lines; `replay-sha256.json` binds the sample, transcript, selection, GIF and poster. Four frames play once for 15 seconds. The site starts on a static poster and requires explicit playback.

For browser QA, serve the repository root on loopback port 8765 in one terminal:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

In another terminal, use your existing installation (set `PLAYWRIGHT_MODULE` to its module path if needed):

```sh
SHOWCASE_LOGS="$SHOWCASE_LOGS/browser" node scripts/showcase/verify-browser.cjs
.venv/bin/python scripts/showcase/verify.py
```

The browser script tests the `/site/` subpath, 1440px and 390px, both themes, both locales, reduced motion, note/source/revision/diff/filter/reset behavior, keyboard activation and native select type selection, manual theme override, explicit replay, errors, no JavaScript, overflow, runtime errors and external requests. It saves screenshots and writes the actual rendered header/hero to `site/assets/banner.png`. Stop the local server when QA is complete. No server is required by Pages beyond serving the static files.

`verify.py` checks insertion-only README preservation against `origin/main`, exact original shell/text blocks and headings, local asset links, public path/copy constraints, replay hashes/line provenance, contrast pairs and GIF size. The original 50-test suite remains the CLI behavior check. There is no configured lint/typecheck tool. Lighthouse was not available in this environment; no performance measurements are claimed.

The logo was supplied by the parent after image generation and inspection. `logo-original.png` is an unchanged copy; `logo.png` is a non-destructive 256px derivative. Banner and poster reuse that same mark. There are no stock assets, external scripts/fonts, trackers, uploads, accounts, browser persistence or model calls. All runtime data and asset URLs are relative. GitHub links intentionally leave the static site.

The Pages workflow uploads only `site/`, runs on relevant main pushes or explicit dispatch, and uses pinned official actions. Action tags were verified through upstream `git ls-remote`: checkout v7.0.1, configure-pages v6.0.0, upload-pages-artifact v5.0.0 and deploy-pages v5.0.1. It has no PR trigger. Publication and service verification are the supervising parent's responsibility.


Current action compatibility was checked against official tagged READMEs, action definitions and release notes: [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [configure-pages](https://github.com/actions/configure-pages/releases/tag/v6.0.0), [upload-pages-artifact](https://github.com/actions/upload-pages-artifact/releases/tag/v5.0.0), [deploy-pages](https://github.com/actions/deploy-pages/releases/tag/v5.0.1). Tag objects were resolved through the GitHub Git refs API, following annotated tag objects if present; all four exact tags resolve directly to commits. Node 24 actions require a compatible runner (checkout documents minimum 2.327.1); this workflow uses GitHub-hosted ubuntu-latest. Checkout v7's fork safety change does not affect this main-only workflow. Upload v5 retains the github-pages artifact name and site path input, adds optional hidden-file inclusion (left false), and pins upload-artifact v7 internally. Deploy v5 retains artifact_name and page_url and changes polling. Configure v6 reads the existing Pages site with enablement false; the build job has pages:read, and only deploy has pages:write/id-token:write. No incompatible contract was found for GitHub.com. Actual hosted deployment remains to be verified by the parent.
