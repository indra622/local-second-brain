// Optional export using an existing Playwright + Chrome installation.
const { chromium } = require('playwright');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 930, height: 540 }, deviceScaleFactor: 2 });
    for (const locale of ['ko', 'en']) {
      const stem = path.join(__dirname, `local-second-brain.${locale}`);
      await page.goto(pathToFileURL(stem + '.svg').href);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: stem + '.png' });
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
