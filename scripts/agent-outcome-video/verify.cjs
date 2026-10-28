// Browser verification for the agent report scenario: scene caption layout, then the site player and explorer.
// Env: OUTCOME_LOGS (required, outside the checkout), SHOWCASE_URL (loopback site root; omit to check the scene only),
//      PLAYWRIGHT_MODULE (default: playwright-core).
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright-core');
const fs = require('node:fs'); const path = require('node:path'); const assert = require('node:assert/strict');
(async () => {
  const out = process.env.OUTCOME_LOGS, base = process.env.SHOWCASE_URL;
  assert(out, 'Set OUTCOME_LOGS outside the checkout'); fs.mkdirSync(out, {recursive: true});
  const b = await chromium.launch({channel: 'chrome', headless: true}); const results = [];
  try {
    const art = await b.newPage({viewport: {width: 1920, height: 1080}});
    for (const lang of ['ko', 'en']) {
      await art.goto(require('node:url').pathToFileURL(path.resolve(__dirname, 'scene.html')).href + '?lang=' + lang);
      await art.evaluate(() => document.fonts.ready);
      const r = await art.evaluate(() => { __overflows.length = 0; for (let t = 0; t < TOTAL; t += 0.1) render(t); const seen = new Map(); for (const o of __overflows) if (!seen.has(o.s)) seen.set(o.s, o); return {total: TOTAL, beats: beats.length, overflows: [...seen.values()]}; });
      assert.equal(r.total, 37.5); assert.equal(r.beats, 6); assert.deepEqual(r.overflows, [], JSON.stringify(r.overflows));
      results.push(`${lang} scene: 37.5 s, 6 beats, every 0.1 s rendered, no caption or label overflow PASS`);
    }
    await art.close();
    if (!base) { console.log(results.join('\n')); return; }
    assert.equal(new URL(base).hostname, '127.0.0.1');
    for (const width of [1440, 390]) for (const colorScheme of ['light', 'dark']) for (const lang of ['en', 'ko']) {
      const p = await b.newPage({viewport: {width, height: 1000}, colorScheme, reducedMotion: 'reduce'});
      const errors = [], requests = []; p.on('pageerror', e => errors.push(e.message)); p.on('request', r => requests.push(r.url()));
      await p.goto(base + 'site/?lang=' + lang);
      const v = p.locator('#scenario-video');
      await p.waitForFunction(() => document.querySelector('video').readyState >= 1);
      const state = await v.evaluate(v => ({duration: v.duration, w: v.videoWidth, h: v.videoHeight, paused: v.paused, autoplay: v.autoplay, loop: v.loop, controls: v.controls, inline: v.playsInline, src: v.currentSrc, poster: v.poster, track: v.querySelector('track').src, fallback: v.querySelector('a').href, name: v.getAttribute('aria-label')}));
      assert.equal(state.duration, 37.5); assert.equal(state.w, 1920); assert.equal(state.h, 1080);
      assert(state.paused && !state.autoplay && !state.loop && state.controls && state.inline);
      for (const k of ['src', 'poster', 'track', 'fallback']) assert(state[k].includes('agent-report-v2-' + lang + '.'), k + ' ' + state[k]);
      assert(state.name && state.name.length > 10);
      assert((await p.locator('#scenario-text').getAttribute('href')).endsWith('agent-report-v2-' + lang + '.txt'));
      assert((await p.locator('#scenario-download').getAttribute('href')).endsWith('agent-report-v2-' + lang + '.mp4'));
      const caption = await p.locator('#scenario-caption').innerText();
      assert(!/choose|paste|골라|붙여/.test(caption), caption);
      assert(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await v.evaluate(v => { v.textTracks[0].mode = 'showing'; return v.play(); }); await p.waitForTimeout(450);
      assert(await v.evaluate(v => v.currentTime > .1 && !v.paused));
      await v.evaluate(v => v.pause()); const paused = await v.evaluate(v => v.currentTime); await p.waitForTimeout(180);
      assert.equal(await v.evaluate(v => v.currentTime), paused);
      for (const time of [4.9, 5.1, 11.9, 12.1, 18.9, 19.1, 26.9, 27.1, 32.9, 33.1, 37]) {
        await v.evaluate((v, t) => new Promise(resolve => { v.addEventListener('seeked', resolve, {once: true}); v.currentTime = t; }), time);
        assert(Math.abs(await v.evaluate(v => v.currentTime) - time) < .1, JSON.stringify({width, colorScheme, lang, time}));
        if (width === 1440 && colorScheme === 'light') await v.screenshot({path: path.join(out, `boundary-${lang}-${time}.png`)});
      }
      assert(await v.evaluate(v => v.textTracks[0].activeCues.length > 0));
      if (width === 1440 && colorScheme === 'light') {
        await v.evaluate(v => { v.currentTime = 36.8; return v.play(); });
        await p.waitForFunction(() => document.querySelector('video').ended, null, {timeout: 10000});
        assert.equal(await v.evaluate(v => v.currentTime), 37.5);
      }
      await v.focus(); assert(await v.evaluate(v => document.activeElement === v));
      for (let tab = 0; tab < 20; tab++) { await p.keyboard.press('Tab'); if (await p.locator('#scenario-download').evaluate(el => el === document.activeElement)) break; }
      assert(await p.locator('#scenario-download').evaluate(el => el === document.activeElement));
      // Existing explorer and CLI replay still work on the same page.
      await p.locator('#workbench').waitFor({state: 'visible'});
      assert.match(await p.locator('#body').innerText(), /Thursday/);
      await p.selectOption('#revision', '0'); assert.match(await p.locator('#body').innerText(), /Friday/);
      await p.locator('#compare').click(); assert.match(await p.locator('#body').innerText(), /\+Send.*Thursday/);
      await p.fill('#search', 'zz-no-match'); assert(await p.locator('#no-results').isVisible());
      await p.locator('#reset').click(); assert.match(await p.locator('#body').innerText(), /Thursday/);
      await p.locator('#play').click(); assert.match(await p.locator('#replay-image').getAttribute('src'), /gif$/);
      await p.locator('#play').click(); assert.match(await p.locator('#replay-image').getAttribute('src'), /png$/);
      await p.locator('#theme').click(); assert.equal(await p.locator('html').getAttribute('data-theme'), colorScheme === 'dark' ? 'light' : 'dark'); await p.locator('#theme').click();
      await p.locator('#locale').click(); const other = lang === 'ko' ? 'en' : 'ko';
      await p.waitForFunction(l => document.querySelector('video').currentSrc.includes('agent-report-v2-' + l + '.'), other);
      assert(await p.locator('#scenario-video').evaluate(v => v.paused));
      assert.equal(await p.locator('html').getAttribute('lang'), other);
      await p.screenshot({path: path.join(out, `video-${width}-${colorScheme}-${lang}-switched.png`), fullPage: true});
      assert.deepEqual(errors, []); assert(requests.every(url => url.startsWith(new URL(base).origin + '/')));
      results.push(`${width} ${colorScheme} ${lang}: native controls, 1080p metadata, language-specific source/poster/captions/transcript, no autoplay or loop, play/pause/seek/boundaries${width === 1440 && colorScheme === 'light' ? '/ended' : ''}, captions active, keyboard focus, explorer and CLI replay regression, theme and locale toggle, no page errors or external requests PASS`);
      await p.close();
    }
    console.log(results.join('\n')); fs.writeFileSync(path.join(out, 'agent-video-browser-results.txt'), results.join('\n') + '\n');
  } finally { await b.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
