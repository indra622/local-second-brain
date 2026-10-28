# Reproduce the agent report scenario

This is a silent, captioned 37.5-second scenario in Korean and English. It shows an agent that the user has authorized using the CLI inside one allowed knowledge folder: it searches exact words, reads the matching notes with their sources and current revisions, links them to this week's inputs, and prepares a report draft that the user reviews. The draft, the notes, the names and the dates are fictional and prepared in advance. No model runs, no product GUI and no live recording are represented. The earlier manual-handoff clip (`report-scenario-v1-*`) and its source under `scripts/outcome-video/` stay unchanged.

`scene.html` draws deterministic frames with `render(seconds)` on a 1920x1080 canvas and selects the language from `?lang=ko` or `?lang=en`. It uses local Apple SD Gothic Neo and Helvetica Neue system fonts; nothing is downloaded. Captions are burned into the picture and also written as VTT from the same strings. The closing frame at 37 seconds becomes the poster.

Use existing Chrome, Node, Playwright Core and ffmpeg with libx264. No dependency installation is needed. From the checkout root, with an output directory outside the checkout:

```sh
export OUTCOME_LOGS="<absolute-external-evidence-directory>"
# Optional: PLAYWRIGHT_MODULE="<existing-playwright-core-module>"; otherwise playwright-core is resolved from the module path.
# Optional: FFMPEG="<existing-ffmpeg-executable>"; otherwise ffmpeg is resolved from PATH.
# Optional: LANGS=en to render one language.
node scripts/agent-outcome-video/render.cjs
```

The renderer pipes 900 PNG frames per language to ffmpeg at 24 fps, H264 High / yuv420p with faststart and no audio, and writes `site/assets/agent-report-v2-<lang>.mp4`, `.jpg` and `site/data/agent-report-v2-<lang>.vtt`. The descriptive transcripts `site/data/agent-report-v2-<lang>.txt` are written by hand. Reproducibility covers layout and timing; installed font, Chrome and encoder versions may change exact bytes.

Verify with the loopback range server from the earlier clip, which serves the checkout on 127.0.0.1 only:

```sh
PORT=8938 node scripts/outcome-video/serve.cjs
```

In another terminal:

```sh
export OUTCOME_LOGS="<absolute-external-evidence-directory>"
export SHOWCASE_URL="http://127.0.0.1:8938/"
node scripts/agent-outcome-video/verify.cjs
python3 scripts/agent-outcome-video/verify-assets.py
```

`verify.cjs` renders every 0.1 s of both languages and fails on any caption or label wider than its box, then checks the site player at 1440 and 390 px in light and dark mode for both languages: native controls without autoplay or loop, language-specific source, poster, captions and transcript, play, pause, seeks at every scene boundary, ending, keyboard focus and the language toggle, plus the existing sample explorer and CLI replay. `verify-assets.py` checks encoding, frame count, duration, faststart, captions, posters, transcripts, the absence of private paths in generated files and that the earlier clip files are untouched. Stop the owned server with Ctrl-C afterwards.
