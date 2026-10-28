# Reproduce the report scenario

This is a silent, captioned 34-second scenario using fictional research, report criteria and a prepared outline. The pointer chooses three notes, then activates a manual handoff together with new material. No model runs, product GUI, automatic recall, or cloud service is represented. Existing CLI evidence is separate and unchanged.

`scene.html` draws deterministic frames with `render(seconds)` on a 1280x720 canvas. It uses local Arial and Apple SD Gothic Neo fonts; no fonts, images or scripts are downloaded. The shared scene selects Korean or English from `?lang=ko` or `?lang=en`. Captions are burned into the picture for direct MP4 playback and also provided as VTT. The final report at 31 seconds becomes the poster. Descriptive transcripts include visual actions and source context.

Use existing Chrome, Node, Playwright Core and ffmpeg with libx264. No dependency installation is needed. From the checkout root, with your own existing module path and an output directory outside the checkout:

```sh
export PLAYWRIGHT_MODULE="<existing-playwright-core-module>"
export OUTCOME_LOGS="<absolute-external-evidence-directory>"
# Optional: FFMPEG="<existing-ffmpeg-executable>"; otherwise ffmpeg is resolved from PATH.
node scripts/outcome-video/render.cjs
```

The renderer pipes 816 PNG frames per locale to ffmpeg, at 24fps, H264/yuv420p with faststart, without audio. It saves a complete temporary clip externally before copying it into versioned site assets. It closes and kills its owned encoder on failure and closes its isolated headless browser. Asset budget: 6 MB per locale. Reproducibility covers scene layout and timing; installed font/Chrome/encoder versions may change exact bytes.

Verify with a loopback server that supports byte ranges, which native video seeking needs. The supplied development server binds only to 127.0.0.1 and serves the checkout; it is not deployed. In one terminal:

```sh
PORT=8938 node scripts/outcome-video/serve.cjs
```

In another, with the same existing module and external logs variables:

```sh
export SHOWCASE_URL="http://127.0.0.1:8938/"
node scripts/outcome-video/verify.cjs
SHOWCASE_LOGS="$OUTCOME_LOGS/regressions" node scripts/showcase/verify-browser.cjs
python3 scripts/showcase/verify.py
python3 scripts/outcome-video/verify-assets.py
```

Stop the owned server with Ctrl-C after verification. Check both MP4s with ffprobe (codec, duration, dimensions, frame count), decode each fully with ffmpeg, and inspect contact sheets plus browser boundary screenshots. The browser verifier covers both widths, themes and languages, captions, transcript links, locale changes, reduced motion, native PLAY/PAUSE/SEEK and keyboard focus. Existing showcase verification retains sample/revision/filter/reset/replay/fallback and original evidence hashes. No CLI, sample fixture, source data or replay binding changes are needed.

The site uses native controls with no autoplay or loop. VTT is optional because readable main captions are already present in the video. README thumbnails link to the hosted MP4, with a separate link to the matching locale page and a descriptive transcript. Hosted links require publication of this commit; this worker does not deploy.
