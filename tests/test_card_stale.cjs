const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
let Card;vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../ha_bundle/www/ania-remote.js'),'utf8'),{HTMLElement:class{},customElements:{define:(_,c)=>Card=c},window:{},Date,Number,Math,setInterval,clearInterval,setTimeout});
(async()=>{
 const c=new Card(),nodes={};c.shadowRoot={};c.config={enable_commands:true,enable_modes:true};c.el=id=>nodes[id]??=( {value:'17',classList:{toggle(){}},disabled:false});c.hasService=()=>true;c.reading=()=>({known:true,fresh:false,mode:'AUTO',value:17,stamp:Date.now()-20000});c.update();
 assert(c.el('plus').disabled);assert(c.el('minus').disabled);assert(!c.el('mode_P1').disabled);assert(!c.el('mode_AUTO').disabled);
 const calls=[];c.call=async(name,data)=>{calls.push([name,data]);return {status:'confirmed'}};c.accept=()=>{};await c.command('plus');assert.equal(calls.length,0);await c.command('P1');assert.equal(calls.length,1);assert.equal(calls[0][0],'ania_mode');assert.equal(calls[0][1].mode,'P1');
 c.reading=()=>({known:true,fresh:true,mode:'SHUTDOWN',stamp:Date.now()});c.update();assert(c.el('mode_P1').disabled);assert(c.el('plus').disabled);
 console.log('Stale: explicit mode selection only; no temperature step; shutdown blocked; one HA call.');
})().catch(e=>{console.error(e);process.exit(1)});
