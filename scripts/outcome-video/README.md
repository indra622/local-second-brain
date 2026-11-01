# Archived v1 report scenario (34 seconds only)

This is a silent, captioned 34-second scenario using fictional research, report criteria and a prepared outline. The pointer chooses three notes, then activates a manual handoff together with new material. No model runs, product GUI, automatic recall, or cloud service is represented. Existing CLI evidence is separate and unchanged.

`scene.html` draws deterministic frames with `render(seconds)` on a 1280x720 canvas. It uses local Arial and Apple SD Gothic Neo fonts; no fonts, images or scripts are downloaded. The shared scene selects Korean or English from `?lang=ko` or `?lang=en`. Captions are burned into the picture for direct MP4 playback and also provided as VTT. The final report at 31 seconds becomes the poster. Descriptive transcripts include visual actions and source context.

Use existing Chrome, Node, Playwright Core and ffmpeg with libx264. No dependency installation is needed. From the checkout root, with your own existing module path and an output directory outside the checkout:

```sh
export PLAYWRIGHT_MODULE="<existing-playwright-core-module>"
export OUTCOME_LOGS="<absolute-external-evidence-directory>"
# Optional: FFMPEG="<existing-ffmpeg-executable>"; otherwise ffmpeg is resolved from PATH.
node scripts/outcome-video/render.cjs
```

The renderer pipes 816 PNG frames per locale to ffmpeg, at 24fps, H264/yuv420p with faststart, without audio. It saves a complete temporary clip externally before copying it into versioned archive/showcase assets. It closes and kills its owned encoder on failure and closes its isolated headless browser. Asset budget: 6 MB per locale. Reproducibility covers scene layout and timing; installed font/Chrome/encoder versions may change exact bytes.

Verify with a loopback server that supports byte ranges, which native video seeking needs. The supplied development server binds only to 127.0.0.1 and serves the checkout; it is not deployed. In one terminal:

```sh
PORT=8938 node scripts/outcome-video/serve.cjs
```

In another, with the same existing module and external logs variables:

```sh
export SHOWCASE_URL="http://127.0.0.1:8938/"
node scripts/outcome-video/verify.cjs
python3 scripts/outcome-video/verify-assets.py
```

Stop the owned server with Ctrl-C after verification. verify-assets.py decodes the archived
34-second pair and checks its encoding, frames, posters, captions and transcripts. The v1
browser check measures old scene captions and archived native-video metadata only; it
must not assert that the current site's player is34 seconds. Use the current QA route
for1440/390 light/dark EN/KO interaction and37.5-second playback.

The original v1 publication used linked README thumbnails. Those are historical details,
not current README requirements. Old deployed v1 asset URLs intentionally retire; repository
files remain in [the archive](../../archive/README.md). Current player QA/reproduction:
[agent-outcome-video](../agent-outcome-video/README.md). The shared range server remains
here and is unchanged.
