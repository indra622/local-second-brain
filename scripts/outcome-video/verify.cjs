// Archived v1 QA only (34 seconds); current site uses agent-outcome-video v2.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
(async()=>{const out=process.env.OUTCOME_LOGS,base=process.env.SHOWCASE_URL;assert(out&&base);fs.mkdirSync(out,{recursive:true});const b=await chromium.launch({channel:'chrome',headless:true});const results=[];try{
const art=await b.newPage({viewport:{width:1280,height:720}});for(const lang of ['en','ko']){await art.goto(require('node:url').pathToFileURL(path.resolve(__dirname,'scene.html')).href+'?lang='+lang);let widths=await art.evaluate(()=>captions.map(s=>{c.font='700 44px Arial, "Apple SD Gothic Neo", sans-serif';return [s,c.measureText(s).width]}));assert(widths.every(([s,w])=>w<=1152),JSON.stringify(widths));results.push(lang+' main caption widths <=1152: '+JSON.stringify(widths));}await art.close();
for(const lang of ['en','ko']) {
 const p=await b.newPage();
 await p.goto(base);
 await p.setContent(`<video controls playsinline preload="metadata"><source src="${base}archive/showcase/assets/report-scenario-v1-${lang}.mp4" type="video/mp4"><track kind="captions" src="${base}archive/showcase/data/report-scenario-v1-${lang}.vtt" srclang="${lang}"></video>`);
 await p.waitForFunction(()=>document.querySelector('video').readyState>=1);
 assert.equal(await p.locator('video').evaluate(v=>v.duration),34);
 await p.close(); results.push(lang+' archived v1: 34-second native metadata PASS (not current site)');
}
console.log(results.join('\n'));fs.writeFileSync(path.join(out,'v1-browser-results.txt'),results.join('\n'));}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
