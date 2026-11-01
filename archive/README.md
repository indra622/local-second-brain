# Preserved showcase material (not deployed)

The eleven files in `showcase/manifest.json` were moved byte-for-byte from `site/` at
base `9efad1ca5cfd9398b5f1fd06470a9528dee605fc`. The manifest records original/new paths,
SHA-256, sizes and Git modes: 1,407,122 bytes total. Git tracks executable status, not
all local checkout permission bits. No image or video was regenerated.

The v1 pair is a 34-second manual-handoff illustration. Its source remains under
`scripts/outcome-video/`; its renderer now targets this archive. That directory's range
server is still used for current v2 browser QA. `logo-original.png`, vision artwork and
banner are preserved here as source/history, not current public assets.

Pages still uploads the entire `site/` directory. This archive is outside that payload.
**The former deployed `assets/report-scenario-v1-*`, `data/report-scenario-v1-*`,
`assets/logo-original.png`, `assets/second-brain-vision-v01.webp` and `assets/banner.png`
URLs are intentionally retired on the next deployment.** No redirect or external-bookmark
compatibility is claimed; files remain available in the repository archive/history.
Moving files does not shrink existing Git history or clone size.

`qa-gates/*.txt` preserves actual old check code from the same base. The showcase gate
froze README prose against3aa15aa; the v1 gate bounded a one-time diff against1870964.
These are historical evidence, not runnable current QA or instructions to restore wording.
Use [the current verification route](../scripts/showcase/README.md).
