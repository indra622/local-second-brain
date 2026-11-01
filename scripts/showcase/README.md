# Current showcase verification

Run from the checkout with existing Python, ImageMagick, ffmpeg/ffprobe, Playwright and
Chrome. Nothing installs tools. Current static QA is independent of historical README
wording or a past PR's permitted diff. Do not regenerate approved assets for verification.

## Reliable current route

```sh
# Use the project interpreter (PyYAML is needed by CLI tests).
PYTHONPATH="$PWD/src" .venv/bin/python -m unittest discover -s tests -v
python3 scripts/showcase/verify.py
python3 scripts/showcase/test_verify.py
python3 scripts/agent-outcome-video/verify-assets.py
# In a separate terminal, keep the owned range server running:
PORT=8938 node scripts/outcome-video/serve.cjs
```

With that server running, in another terminal:

```sh
export SHOWCASE_URL="http://127.0.0.1:8938/"
export PLAYWRIGHT_MODULE="<absolute-path-to-existing-playwright-module>"
export SHOWCASE_LOGS="<absolute-external-logs-directory>/showcase"
export OUTCOME_LOGS="<absolute-external-logs-directory>/video"
node scripts/showcase/verify-browser.cjs
node scripts/agent-outcome-video/verify.cjs
```

Stop the owned server with Ctrl-C afterward. Browser suites cover1440/390, light/dark,
EN/KO, source/current/revision/diff/search/miss/reset, replay/focus, playback/pause/seek/end,
captions/transcript/locale, no overflow/page errors/external requests, no-JS and error fallback.
Screenshots/results go only to the explicit external directories. No banner is written.

`verify.py` checks local links, active v2 references, EN/KO outcome consistency, approved
active/source SHA-256, archived bytes/Git executable modes and exclusion from site payload,
CLI replay hashes/excerpt provenance, semantic sample outputs, contrast and GIF budget.
`test_verify.py` rejects broken links, wrong active version and false proof/semantic output,
even when fixture proof hashes are rebound. Preservation is based on current documented
asset paths/manifests, not origin/main or a fixed past whole README. Approved changes to
assets require deliberate manifest updates; tests do not regenerate assets or baselines.

## Reproduction (changes outputs; not QA)

Only when intentionally reproducing new evidence, use existing tools:

```sh
PYTHONPATH="$PWD/src" .venv/bin/python scripts/showcase/generate.py --logs /tmp/new-showcase-raw
.venv/bin/python scripts/showcase/render.py --frames /tmp/new-showcase-frames
```

Synthetic fixtures drive actual CLI operations; sample/transcript retain full outputs,
while replay-selection derives excerpts and replay-sha256 binds artifacts. Temporary
bundles are removed. Display paths are aliases, and actual capture timestamps make a
new generation byte-different. The generator asserts unchanged earlier source/revision,
exact source/body bytes, current selection and clean check. No model produces the sample.

Old34-second v1 verification is version-specific under `scripts/outcome-video/`; current
37.5-second v2 checks are under `scripts/agent-outcome-video/`. Eleven inactive files and
actual old gate code are [archived](../../archive/README.md), not deleted. Their old deployed
URLs retire intentionally. Pages continues uploading only `site/`; no new infrastructure.

Historical statements below remain dated evidence, not current test counts or a fresh
CI/deployment claim. No Lighthouse/performance result is claimed by this route.
## Historical deployment notes (preserved from9efad1c)

Action compatibility was checked against official tagged READMEs, action definitions and release notes: [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [configure-pages](https://github.com/actions/configure-pages/releases/tag/v6.0.0), [upload-pages-artifact](https://github.com/actions/upload-pages-artifact/releases/tag/v5.0.0), [deploy-pages](https://github.com/actions/deploy-pages/releases/tag/v5.0.1). Tag objects were resolved through the GitHub Git refs API, following annotated tag objects if present; all four exact tags resolve directly to commits. Node 24 actions require a compatible runner (checkout documents minimum 2.327.1); this workflow uses GitHub-hosted ubuntu-latest. Checkout v7's fork safety change does not affect this main-only workflow. Upload v5 retains the github-pages artifact name and site path input, adds optional hidden-file inclusion (left false), and pins upload-artifact v7 internally. Deploy v5 retains artifact_name and page_url and changes polling. Configure v6 reads the existing Pages site with enablement false; the build job has pages:read, and only deploy has pages:write/id-token:write. No incompatible contract was found for GitHub.com. Actual hosted deployment remains to be verified by the parent.
