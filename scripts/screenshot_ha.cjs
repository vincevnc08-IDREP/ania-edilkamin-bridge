// npm install playwright && npx playwright install chromium
// Start a local HTTP server at repository root first (port 8765).
const {chromium}=require('playwright');
const path=require('path');
(async()=>{const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:1200,height:790},deviceScaleFactor:1.5});
 await page.goto('http://127.0.0.1:8765/docs/ha_preview.html');
 await page.waitForFunction(()=>document.getElementById('fresh').shadowRoot?.getElementById('value').textContent==='20 °C');
 const result=await page.evaluate(()=>({fresh:document.getElementById('fresh').el('plus').disabled,stale:document.getElementById('stale').el('plus').disabled,apply:document.getElementById('fresh').el('apply').disabled}));
 if(result.fresh||!result.stale||result.apply)throw Error('Incorrect preview states');
 await page.screenshot({path:path.join(__dirname,'../docs/assets/ha_card.png'),fullPage:true});
 console.log('Preview verified: confirmed state enabled; stale state disabled.');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
