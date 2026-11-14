const {chromium}=require('playwright'),assert=require('assert'),path=require('path');
(async()=>{const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:1150,height:850}});
 await page.setContent('<style>body{background:#101d2c;color:#ecf4ff;font:16px system-ui;padding:35px}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}h1{font-size:25px}</style><h1>ANIA · Auto, puissances et Power 3 s</h1><p>Démonstration locale — aucune liaison radio</p><main><ania-remote id="auto"></ania-remote><ania-remote id="manual"></ania-remote></main>');
 await page.addScriptTag({content:"customElements.define('ha-card',class extends HTMLElement{constructor(){super();this.attachShadow({mode:'open'}).innerHTML='<style>:host{display:block}</style><slot></slot>'}})"});
 await page.addScriptTag({path:path.join(__dirname,'../ha_bundle/www/ania-remote.js')});
 await page.evaluate(()=>{window.calls=[];for(const id of ['auto','manual']){let c=document.getElementById(id);c.setConfig({enable_commands:true});c.hass={states:{'sensor.ania_radio':{state:'confirmed',attributes:{mode:id==='auto'?'AUTO':'MANUAL',power_mode:id==='manual'?2:null,setpoint_c:id==='auto'?17:null,observed_epoch:Date.now()/1000},last_updated:new Date().toISOString()}},services:{script:{ania_plus:{},ania_minus:{},ania_mode:{},ania_setpoint:{},ania_power:{}}},callService:async(d,s,data)=>{window.calls.push({s,data});await new Promise(r=>setTimeout(r,50));return {response:s==='ania_power'?{status:'sent',hold_ms:3000,release_sent:true,power_state:null}:{status:'confirmed',mode:'MANUAL',power_mode:1,setpoint_c:null,observed_at:Date.now()/1000}}}}}});
 await page.screenshot({path:path.join(__dirname,'../docs/assets/ha_card.png'),fullPage:true});
 assert.equal(await page.evaluate(()=>document.getElementById('manual').el('value').textContent),'P2');
 await page.evaluate(()=>{let c=document.getElementById('auto');c.el('power').click();c.el('power').click()});
 await page.waitForFunction(()=>document.getElementById('auto').message.includes('Power envoyé'));
 let result=await page.evaluate(()=>({calls:window.calls,value:document.getElementById('auto').el('value').textContent,disabled:document.getElementById('auto').el('power').disabled}));assert.equal(result.calls.length,1);assert.equal(result.calls[0].s,'ania_power');assert.equal(result.value,'17 °C');assert(result.disabled);
 console.log('DOM: modes visibles, Power envoyé une seule fois, temporisation, aucune inférence marche/arrêt.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
