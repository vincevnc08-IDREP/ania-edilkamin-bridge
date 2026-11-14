/** v6: observed state and requested target remain separate; no blind RF retry. */
class AniaRemote extends HTMLElement {
  constructor(){super();this.busy=false;this.message='';this.dirty=false;}
  setConfig(config){
    this.config={entity:'sensor.ania_consigne',enable_commands:false,max_age_seconds:90,...config};
    if(!this.shadowRoot)this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<style>
    :host{display:block;color:#ecf4ff}ha-card{padding:22px;border:1px solid #30415a;border-radius:22px;background:linear-gradient(135deg,#173436,#172035 65%,#29213e)}
    .eyebrow{color:#69deca;font-size:11px;letter-spacing:2px;font-weight:700}h2{margin:9px 0 18px;font-size:23px}.remote{display:grid;grid-template-columns:60px 1fr 60px;gap:12px;align-items:center;text-align:center}
    button,input{font:inherit;border:1px solid #446078;border-radius:14px;min-height:48px;box-sizing:border-box}button{background:#24364b;color:#ecf4ff;cursor:pointer}button:disabled{opacity:.4;cursor:not-allowed}button:focus-visible,input:focus-visible{outline:3px solid #ffd166;outline-offset:3px}.step{height:60px;font-size:32px;background:#5ce3cb;color:#102b31;font-weight:700;border:0}
    #value{font-size:38px;font-weight:750;color:#ffd166}.stale{opacity:.65}.label,.note{font-size:12px;color:#b2c2d4;line-height:1.5}.target{display:grid;grid-template-columns:1fr 110px;gap:10px;margin-top:18px}.target label{display:block;font-size:12px;color:#b2c2d4;margin-bottom:6px}input{width:100%;background:#122638;color:#fff;padding:8px 12px;font-size:20px}#apply{align-self:end;background:#5ce3cb;color:#102b31;font-weight:700}#status{min-height:42px;font-size:13px;line-height:1.5;margin-top:16px;color:#cbd8e5}.note{border-top:1px solid #30415a;padding-top:12px;margin:12px 0 0}.pill{display:inline-block;margin-top:10px;font-size:11px;border-radius:20px;padding:5px 9px;background:#23394a;color:#b2c2d4}
    @media(max-width:360px){ha-card{padding:16px}.remote{grid-template-columns:48px 1fr 48px;gap:8px}#value{font-size:32px}}
    </style><ha-card><div class="eyebrow">ANIA / CONFORT</div><h2>Poêle Ania</h2>
    <div class="remote"><button class="step" id="minus" aria-label="Diminuer la consigne">−</button><div><div id="value">—</div><div class="label" id="label">Lecture en cours</div></div><button class="step" id="plus" aria-label="Augmenter la consigne">+</button></div>
    <div class="target"><div><label for="target">Nouvelle consigne · 10 à 25 °C</label><input id="target" type="number" inputmode="numeric" min="10" max="25" step="1" aria-label="Nouvelle consigne en degrés"></div><button id="apply">Valider</button></div>
    <div id="status" role="status" aria-live="polite"></div><span class="pill">Passerelle Wi-Fi</span><p class="note">Marche/arrêt et P1–P3 seront ajoutés après fiabilisation.</p></ha-card>`;
    for(const d of ['plus','minus'])this.el(d).onclick=()=>this.command(d);
    this.el('target').oninput=()=>{this.dirty=true;this.update();};
    this.el('target').onkeydown=e=>{if(e.key==='Enter'&&!this.el('apply').disabled)this.command('target');};
    this.el('apply').onclick=()=>this.command('target');this.update();
  }
  el(id){return this.shadowRoot.getElementById(id);}
  set hass(h){this.h=h;this.update();if(!this.busy&&!this.resumed){this.resumed=true;let id;try{id=sessionStorage.getItem('ania-target-job');}catch{}if(id)this.resume(id);}}
  getCardSize(){return 5;}
  connectedCallback(){this.timer=setInterval(()=>this.update(),1000);}
  disconnectedCallback(){clearInterval(this.timer);}
  reading(){
    const raw=this.h?.states['sensor.ania_radio'];const entity=this.h?.states[this.config.entity];
    const a=raw?.attributes||entity?.attributes||{};
    const value=raw?a.setpoint_c:Number(entity?.state);
    const stamp=typeof a.observed_epoch==='number'?a.observed_epoch*1000:Date.parse(a.observed_at||'');
    const known=typeof value==='number'&&Number.isFinite(value)&&Number.isFinite(stamp)&&stamp<=Date.now()+5000;
    const live=(raw?raw.state==='confirmed':!['unavailable','unknown'].includes(entity?.state));
    if(known&&(!this.last||stamp>=this.last.stamp))this.last={value,stamp};
    if(this.confirmed&&(!this.last||this.confirmed.stamp>=this.last.stamp))this.last=this.confirmed;
    const localNewer=this.confirmed&&this.confirmed.stamp>stamp&&Date.parse(raw?.last_updated||'')<=this.confirmed.receivedAt;
    const fresh=!!this.last&&(live||localNewer)&&Date.now()-this.last.stamp<=this.config.max_age_seconds*1000;
    return {...this.last,known:!!this.last,fresh};
  }
  hasService(name){return !!this.h?.services?.script?.[name];}
  update(){
    if(!this.config||!this.shadowRoot)return;
    const r=this.reading(),age=r.known?Math.max(0,Math.floor((Date.now()-r.stamp)/1000)):0;
    if(this.waitAfter&&r.fresh&&r.stamp>this.waitAfter){this.waitAfter=0;this.message='';}
    this.el('value').textContent=r.known?r.value.toLocaleString('fr-FR')+' °C':'—';
    this.el('value').classList.toggle('stale',!r.fresh);
    this.el('label').textContent=r.fresh?'Consigne confirmée sur le poêle':r.known?'Dernière consigne confirmée':'Première lecture en cours';
    if(!this.dirty&&!this.busy&&r.known)this.el('target').value=String(r.value);
    const disabled=!this.config.enable_commands||this.busy||!!this.waitAfter||!r.fresh;
    this.el('plus').disabled=disabled||r.value>=25||!this.hasService('ania_plus');
    this.el('minus').disabled=disabled||r.value<=10||!this.hasService('ania_minus');
    const v=this.el('target').value,t=Number(v),valid=v.trim()!==''&&Number.isInteger(t)&&t>=10&&t<=25;
    this.el('target').disabled=this.busy;
    this.el('apply').disabled=disabled||!valid||t===r.value||!this.hasService('ania_setpoint');
    this.el('apply').textContent=this.busy?'En cours…':'Valider';
    this.el('status').textContent=this.busy?this.progress||'Envoi de la demande…':this.message||(!r.fresh?(r.known?'Lecture datant de '+(age<60?age+' s':Math.floor(age/60)+' min')+' · reconnexion en cours. Commandes suspendues.':'Connexion au poêle en cours…'):this.waitAfter?'Attente d’une nouvelle lecture avant le prochain appui.':'Lecture reçue il y a '+age+' s'+(this.latency?' · dernier changement confirmé en '+this.latency+' s.':'.'));
  }
  async call(service,data={}){return (await this.h.callService('script',service,data,undefined,false,true))?.response;}
  accept(data){
    const stamp=typeof data.observed_at==='number'?data.observed_at*1000:Date.parse(data.observed_at||'');
    if(typeof data.setpoint_c!=='number'||!Number.isFinite(stamp)||Date.now()-stamp>90000||stamp>Date.now()+5000)throw Error('Confirmation radio trop ancienne.');
    this.confirmed={value:data.setpoint_c,stamp,receivedAt:Date.now()};
  }
  async follow(id){
    try{sessionStorage.setItem('ania-target-job',id);}catch{}
    const end=Date.now()+160000;
    while(Date.now()<end){
      const data=await this.call('ania_target_progress',{request_id:id});
      if(data?.status==='confirmed'){this.accept(data);try{sessionStorage.removeItem('ania-target-job');}catch{}return;}
      if(data?.status!=='in_progress'){try{sessionStorage.removeItem('ania-target-job');}catch{}throw Error('Réglage interrompu. Attendre une nouvelle lecture ; aucune commande n’est répétée.');}
      if(typeof data.setpoint_c==='number')this.accept(data);
      this.progress='Vers '+data.target_c+' °C · '+(data.steps_confirmed||0)+' degré(s) confirmé(s)…';this.update();
      await new Promise(resolve=>setTimeout(resolve,1500));
    }
    throw Error('Suivi interrompu. La prochaine ouverture relira la demande sans la renvoyer.');
  }
  async resume(id){this.busy=true;this.progress='Reprise du suivi de la demande…';this.update();try{await this.follow(id);}catch(e){this.message=e.message;this.waitAfter=Date.now();}finally{this.busy=false;this.update();}}
  async command(direction){
    if(this.busy||this.waitAfter||!this.config.enable_commands||!this.reading().fresh)return;
    if(direction==='target'&&this.el('apply').disabled)return;
    if(direction!=='target'&&!['plus','minus'].includes(direction))return;
    const start=Date.now();this.busy=true;this.message='';this.progress=direction==='target'?'Demande de '+this.el('target').value+' °C…':'Demande '+(direction==='plus'?'+1':'−1')+' °C · confirmation en cours…';this.update();
    try{
      const data=await this.call(direction==='target'?'ania_setpoint':'ania_'+direction,direction==='target'?{target_c:Number(this.el('target').value)}:{});
      if(data?.status==='in_progress'&&data.request_id)await this.follow(data.request_id);
      else if(data?.status==='confirmed')this.accept(data);
      else throw Error(data?.status==='not_sent'||data?.status==='busy'?'Commande non envoyée : liaison occupée.':'Retour non confirmé. Attendre une nouvelle lecture avant un nouvel appui.');
      this.latency=((Date.now()-start)/1000).toLocaleString('fr-FR',{maximumFractionDigits:1});this.dirty=false;this.waitAfter=0;
    }catch(e){this.message=e.message||'Demande non confirmée.';this.waitAfter=Date.now();}
    finally{this.busy=false;this.update();}
  }
}
customElements.define('ania-remote',AniaRemote);
window.customCards=window.customCards||[];window.customCards.push({type:'ania-remote',name:'ANIA · Télécommande Ania',description:'Consigne confirmée, boutons et saisie avec validation.'});
