// Existing Playwright, Chrome and ffmpeg only; intermediate evidence stays outside the checkout.
// Env: PLAYWRIGHT_MODULE (default: playwright-core from the module path), FFMPEG (default: ffmpeg on PATH),
//      OUTCOME_LOGS (required, outside the checkout), LANGS (default: ko,en).
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {once} = require('node:events');

const FPS = 24;
(async () => {
  const root = path.resolve(__dirname, '../..');
  const logs = process.env.OUTCOME_LOGS;
  const relative = logs && path.relative(root, path.resolve(logs));
  if (!logs || !(relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative))) {
    throw Error('Set OUTCOME_LOGS outside the checkout');
  }
  const ffmpeg = process.env.FFMPEG || 'ffmpeg';
  const langs = (process.env.LANGS || 'ko,en').split(',');
  fs.mkdirSync(logs, {recursive: true});
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const lang of langs) {
      const page = await browser.newPage({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1});
      page.on('pageerror', error => { throw error; });
      await page.goto(pathToFileURL(path.join(__dirname, 'scene.html')).href + '?lang=' + lang);
      await page.evaluate(() => document.fonts.ready);
      const {total, beats} = await page.evaluate(() => ({total: TOTAL, beats}));
      const frames = Math.round(total * FPS);
      const stem = path.join(root, `site/assets/agent-report-v2-${lang}`);
      // A failed render must leave the last complete public clip intact.
      const pending = path.join(logs, `pending-${lang}.mp4`);
      const ff = spawn(ffmpeg, ['-y', '-f', 'image2pipe', '-vcodec', 'png', '-framerate', String(FPS), '-i', '-',
        '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-r', String(FPS), pending]);
      const log = fs.createWriteStream(path.join(logs, `render-${lang}.log`));
      ff.stderr.pipe(log);
      let failure;
      ff.on('error', error => { failure = error; });
      ff.stdin.on('error', error => { failure = error; });
      const done = new Promise(resolve => ff.once('close', code => resolve(code)));
      try {
        for (let i = 0; i < frames; i++) {
          // Canvas pixels only, independent of page layout or compositor timing.
          const bytes = Buffer.from(await page.evaluate(t => { render(t); return document.getElementById('c').toDataURL('image/png').slice(22); }, i / FPS), 'base64');
          if (failure || ff.exitCode !== null || ff.signalCode !== null) throw failure || Error('Encoder exited early');
          if (!ff.stdin.write(bytes)) {
            await Promise.race([once(ff.stdin, 'drain'), done.then(() => { throw failure || Error('Encoder exited early'); })]);
          }
          if (i % 120 === 0) console.log(lang, i + '/' + frames);
        }
        ff.stdin.end();
        const code = await done;
        if (failure || code) throw failure || Error('ffmpeg ' + code);
      } finally {
        if (ff.exitCode === null && ff.signalCode === null) {
          ff.stdin.destroy();
          ff.kill('SIGKILL');
          await done;
        }
      }
      fs.copyFileSync(pending, stem + '.mp4');
      fs.unlinkSync(pending);
      // Poster: the closing frame with the wordmark fully visible.
      execFileSync(ffmpeg, ['-y', '-ss', '37', '-i', stem + '.mp4', '-frames:v', '1', '-q:v', '2', stem + '.jpg'], {stdio: 'ignore'});
      const stamp = s => `00:${String(Math.floor(s / 60)).padStart(2, '0')}:${(s % 60).toFixed(3).padStart(6, '0')}`;
      fs.writeFileSync(path.join(root, `site/data/agent-report-v2-${lang}.vtt`), 'WEBVTT\n\n' + beats.map(b =>
        `${stamp(b.start)} --> ${stamp(b.start + b.dur)} line:80%\n${b.head}\n`).join('\n'));
      await page.close();
      console.log('COMPLETE ' + stem + '.mp4 frames ' + frames);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
