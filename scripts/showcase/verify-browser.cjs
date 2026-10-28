// Use an existing Playwright installation; no browser or dependency install.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const out = process.env.SHOWCASE_LOGS;
  assert(out, 'Set SHOWCASE_LOGS to a directory outside the checkout');
  const relativeOut = path.relative(process.cwd(),path.resolve(out));
  assert(relativeOut === '..' || relativeOut.startsWith('..'+path.sep), 'Logs must be outside the checkout');
  fs.mkdirSync(out,{recursive:true});
  const base = process.env.SHOWCASE_URL;
  assert(base && new URL(base).hostname === '127.0.0.1', 'Set SHOWCASE_URL to the owned loopback server');
  async function checkVision(page, language, width, mode) {
    const img = page.locator('#vision-image');
    await img.evaluate(el => el.decode());
    assert.match(await img.getAttribute('alt'), language === 'ko' ? /미래 비전.*오늘의 질문.*보고서/ : /Future vision:.*today’s question.*report/);
    assert.equal(await img.getAttribute('loading'),null);
    assert.equal(await img.getAttribute('width'),'1672');
    assert.equal(await img.getAttribute('height'),'941');
    assert.equal(await page.locator('#vision-label').innerText(), language === 'ko' ? '우리가 지향하는 Second Brain' : 'The Second Brain we are building toward');
    assert.match(await page.locator('[data-t=visionLimit]').innerText(), language === 'ko' ? /비전 일러스트.*현재는.*명령줄 도구/ : /vision illustration, not a current product screen.*command-line tool/);
    assert.match(await page.locator('[data-t=visionBody]').innerText(), language === 'ko' ? /자료.*결정.*질문.*보고서/ : /sources.*decisions.*question.*report/);
    assert(await img.evaluate(el => {
      const box=el.getBoundingClientRect(), style=getComputedStyle(el);
      return el.naturalWidth === 1672 && el.naturalHeight === 941 &&
        Math.abs(box.width / box.height - 1672 / 941) < .005 &&
        box.width >= document.querySelector('main').clientWidth - 1 &&
        style.objectFit !== 'cover' && box.left >= 0 && box.right <= innerWidth;
    }));
    assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:path.join(out,`hero-${width}-${mode}-${language}.png`),fullPage:true});
  }
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const results=[];
  try {
    for (const mode of ['light','dark']) for (const width of [1440,390]) {
      const page = await browser.newPage({viewport:{width,height:1000},colorScheme:mode,reducedMotion:'reduce'});
      const errors=[], requests=[];
      page.on('pageerror',e=>errors.push(e.message));
      page.on('request',r=>requests.push(r.url()));
      await page.goto(new URL('site/',base).href);
      await page.locator('#workbench').waitFor({state:'visible'});
      await checkVision(page,'en',width,mode);
      assert.match(await page.locator('#body').innerText(), /Thursday/);
      assert.match(await page.locator('#status').innerText(), /current.*draft.*unverified/);
      await page.selectOption('#revision','0');
      assert.match(await page.locator('#body').innerText(), /Friday/);
      assert.match(await page.locator('#status').innerText(), /earlier/);
      await page.locator('#source-details summary').click();
      assert.match(await page.locator('#sources').innerText(), /Friday/);
      await page.locator('#compare').click();
      assert.match(await page.locator('#body').innerText(), /-Send.*Friday/);
      assert.match(await page.locator('#body').innerText(), /\+Send.*Thursday/);
      await page.locator('#notes button').nth(1).click();
      assert.match(await page.locator('#body').innerText(), /Research handoff/);
      assert(await page.locator('#compare').isDisabled());
      await page.fill('#search','zz-no-match');
      assert(await page.locator('#no-results').isVisible());
      assert(await page.locator('#note-panel').isHidden());
      await page.locator('#reset').click();
      assert.match(await page.locator('#body').innerText(), /Thursday/);
      await page.fill('#search','Friday');
      assert.equal(await page.locator('#notes button').count(),1);
      await page.locator('#reset').click();
      await page.keyboard.press('Tab');
      assert(await page.evaluate(()=>document.activeElement.matches(':focus-visible')));
      assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({path:path.join(out,`${width}-${mode}.png`),fullPage:true});
      await page.locator('#theme').click();
      assert.equal(await page.locator('html').getAttribute('data-theme'),mode==='dark'?'light':'dark');
      await page.locator('#locale').click();
      await page.locator('#workbench').waitFor({state:'visible'});
      assert.equal(await page.locator('html').getAttribute('lang'),'ko');
      assert.match(await page.title(),/대화/);
      assert.match(await page.locator('#note-title').innerText(),/보고서/);
      await checkVision(page,'ko',width,mode);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({path:path.join(out,`${width}-${mode}-ko.png`),fullPage:true});
      await page.locator('#play').click();
      assert.match(await page.locator('#replay-image').getAttribute('src'),/gif$/);
      await page.locator('#play').click();
      assert.match(await page.locator('#replay-image').getAttribute('src'),/png$/);
      assert.deepEqual(errors,[]);
      assert(requests.every(url=>url.startsWith(new URL(base).origin+'/')));
      results.push(`${width}px ${mode}: selection, source, old/current, diff, search/miss/reset, focus, locale, theme, playback, localized vision/alt/claim, full aspect ratio, no overflow or external requests PASS`);
      await page.close();
    }
    const keyboard=await browser.newPage({reducedMotion:'no-preference'});
    await keyboard.goto(new URL('site/',base).href);
    await keyboard.locator('#workbench').waitFor({state:'visible'});
    assert.match(await keyboard.locator('#replay-image').getAttribute('src'),/png$/);
    await keyboard.locator('#notes button').nth(1).focus();
    await keyboard.keyboard.press('Enter');
    assert(await keyboard.locator('#notes button').nth(1).evaluate(el => el === document.activeElement));
    assert.match(await keyboard.locator('#note-title').innerText(),/Research/);
    await keyboard.locator('#reset').focus();
    await keyboard.keyboard.press('Enter');
    await keyboard.locator('#revision').focus();
    await keyboard.keyboard.type('v1');
    await keyboard.keyboard.press('Tab');
    assert.match(await keyboard.locator('#body').innerText(),/Friday/);
    await keyboard.locator('#source-details summary').focus();
    await keyboard.keyboard.press('Enter');
    assert(await keyboard.locator('#sources').isVisible());
    results.push('Keyboard Enter selection/reset/source and native revision type selection PASS; no-preference replay stays static until requested');
    const page=await browser.newPage();
    await page.route('**/data/sample.json',r=>r.fulfill({status:500,body:'error'}));
    await page.goto(new URL('site/',base).href);
    await page.getByText('Could not load the sample.',{exact:false}).waitFor();
    results.push('Data error fallback PASS');
    const nojs=await browser.newPage({javaScriptEnabled:false});
    await nojs.goto(new URL('site/',base).href);
    assert(await nojs.locator('noscript').isVisible());
    results.push('No-JS data/transcript alternative PASS');
    fs.writeFileSync(path.join(out,'browser-results.txt'),results.join('\n')+'\n');
    console.log(results.join('\n'));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
