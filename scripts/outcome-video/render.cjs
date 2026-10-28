// Existing Playwright, Chrome and ffmpeg only; intermediate evidence stays outside checkout.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {once} = require('node:events');

(async () => {
  const root = path.resolve(__dirname, '../..');
  const logs = process.env.OUTCOME_LOGS;
  const relative = logs && path.relative(root, path.resolve(logs));
  if (!logs || !(relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative))) {
    throw Error('Set OUTCOME_LOGS outside the checkout');
  }
  const ffmpeg = process.env.FFMPEG || 'ffmpeg';
  fs.mkdirSync(logs, {recursive: true});
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const lang of ['ko', 'en']) {
      const page = await browser.newPage({viewport: {width: 1280, height: 720}, deviceScaleFactor: 1});
      await page.goto(pathToFileURL(path.join(__dirname, 'scene.html')).href + '?lang=' + lang);
      await page.evaluate(() => document.fonts.ready);
      const stem = path.join(root, `site/assets/report-scenario-v1-${lang}`);
      // A failed render must leave the last complete public clip intact.
      const pending = path.join(logs, `pending-${lang}.mp4`);
      const ff = spawn(ffmpeg, ['-y', '-f', 'image2pipe', '-vcodec', 'png', '-framerate', '24', '-i', '-',
        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '25', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', pending]);
      const log = fs.createWriteStream(path.join(logs, `render-${lang}.log`));
      ff.stderr.pipe(log);
      let failure;
      ff.on('error', error => { failure = error; });
      ff.stdin.on('error', error => { failure = error; });
      const done = new Promise(resolve => ff.once('close', code => resolve(code)));
      try {
        for (let i = 0; i < 816; i++) {
          await page.evaluate(t => render(t), i / 24);
          const bytes = await page.screenshot({type: 'png'});
          if (failure || ff.exitCode !== null || ff.signalCode !== null) throw failure || Error('Encoder exited early');
          if (!ff.stdin.write(bytes)) {
            await Promise.race([once(ff.stdin, 'drain'), done.then(() => { throw failure || Error('Encoder exited early'); })]);
          }
          if (i % 120 === 0) console.log(lang, i + '/816');
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
      execFileSync(ffmpeg, ['-y', '-ss', '31', '-i', stem + '.mp4', '-frames:v', '1', stem + '.jpg'], {stdio: 'ignore'});
      const caps = await page.evaluate(() => captions);
      const ends = [0, 5, 11, 17, 23, 29, 34];
      const stamp = s => `00:${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}.000`;
      fs.writeFileSync(path.join(root, `site/data/report-scenario-v1-${lang}.vtt`), 'WEBVTT\n\n' + caps.map((s, i) =>
        `${stamp(ends[i])} --> ${stamp(ends[i + 1])} line:76%\n${s}${i === 5 ? (lang === 'ko' ? ' 지난 작업을 출발점으로.' : ' then build on what changed.') : ''}\n`).join('\n'));
      await page.close();
      console.log('COMPLETE ' + stem + '.mp4');
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
