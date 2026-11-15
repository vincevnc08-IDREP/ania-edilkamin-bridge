"""Bounded neutral polling and one-shot commands. No HA dependency."""
import os,serial,time,re,json,pathlib,base64,zlib,subprocess,sys,fcntl
import numpy as np
from serial.tools import list_ports
from state import Consensus,parse_frame
from iq_decode import decode_file
OUT=pathlib.Path(os.environ.get('ANIA_CAPTURE_DIR','/tmp/ania-dual-captures'))
class PrecheckError(RuntimeError):
 command_sent=False

class Radio:
 def __init__(self,gain=10):
  if gain not in range(13):raise ValueError('gain 0..12')
  from network_stream import NetworkStream
  self.gain=gain;self.index=0;self.s=None
  self.lock=open('/tmp/ania-dual.lock','w');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  self.out=OUT/(time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()));self.out.mkdir(parents=True)
  self.host=os.environ['ANIA_GATEWAY_HOST'];self.port=int(os.environ.get('ANIA_GATEWAY_PORT','18765'))
  self.token=pathlib.Path(os.environ['ANIA_LINK_TOKEN_FILE']).read_text().strip()
  try:self.connect()
  except Exception:self.close();raise
 def connect(self):
  from network_stream import NetworkStream
  if self.s is not None:self.s.close()
  self.s=NetworkStream(self.host,self.port,self.token)
  status=self.cmd('rx status',rb'^.*mode=RX_TX_MANUAL.*\n',timeout=3)
  if b'version=13 ' not in status or b'ready=1 ' not in status:
   self.s.close();raise RuntimeError(status)
 def close(self):
  if self.s is not None:self.s.close()
  self.lock.close()
 def cmd(self,command,end,timeout=60):
  try:
   self.s.write((command+'\n').encode());raw=bytearray();deadline=time.monotonic()+timeout
   while time.monotonic()<deadline:
    raw.extend(self.s.read(min(max(self.s.in_waiting,1),65536)));clean=re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]',b'',bytes(raw)).replace(b'\r',b'')
    if re.search(end,clean,re.M):return clean
   raise TimeoutError('Commande non répétée : '+command+' '+repr(bytes(raw[-500:])))
  except Exception:self.s.close();raise
 def check(self):
  # This command verifies waveforms in memory and emits no RF. One reconnect
  # is safe here; actual button commands are never replayed.
  for attempt in range(2):
   try:
    if self.s.closed:self.connect()
    raw=self.cmd('tx check',rb'^TX_CHECK[^\n]*\n',timeout=3)
    if b'TX_CHECK rc=0 ready=1' not in raw:raise RuntimeError(raw)
    return
   except (TimeoutError,ConnectionError,OSError):
    if attempt:raise
    self.connect()
 def poll_iq(self,window=8):
  begin=time.monotonic();self.check();checked=time.monotonic();started=time.time();raw=self.cmd(f'tx poll {self.gain} 100 {window}',rb'^RING_END[^\n]*\n')
  received=time.monotonic()
  name=f'{self.index:03d}';self.index+=1;lines=raw.splitlines()
  (self.out/(name+'.log')).write_bytes(b'\n'.join(x for x in lines if not x.startswith(b'd ')))
  def fields(prefix):return {k.decode():int(v) for k,v in re.findall(rb'(\w+)=(-?\d+)',next(x for x in lines if x.startswith(prefix)))}
  m=fields(b'RING ');m.update(fields(b'POLL '));wire=b''.join(base64.b64decode(x[2:],validate=True) for x in lines if x.startswith(b'd '))
  if len(wire)!=m['stored']*2 or zlib.crc32(wire)!=m['crc32']:raise ValueError('Capture SPI/Wi-Fi corrompue')
  mapping=[list(map(int,x[2:].split())) for x in lines if x.startswith(b'M ')]
  if sum(x[2] for x in mapping)!=m['stored']:raise ValueError('Carte échantillons invalide')
  np.asarray(np.frombuffer(wire,dtype='i1').astype('<i2')*4,dtype='<i2').tofile(self.out/(name+'.cs16'));(self.out/(name+'.wire8')).write_bytes(wire)
  m.update(sample_map=mapping,scale=1,continuous_verified=m['stored']==m['requested'] and m['gaps']==0 and m['lost_pairs']==0 and m['rc']==0 and len(mapping)==1,quantization_bits=8,host_poll_time_unix=started,subsample_no_antialias=True,neutral_poll=True)
  (self.out/(name+'.json')).write_text(json.dumps(m,indent=2))
  dest=self.out/(name+'.decoded.json')
  frames=decode_file(self.out/(name+'.cs16'));dest.write_text(json.dumps(frames,indent=2));print(f'poll {name}: {sum(bool(f.get("crc_matches")) for f in frames)} CRC',flush=True)
  m['timing_seconds']={'check':checked-begin,'capture_transfer':received-checked,'parse_decode_save':time.monotonic()-received,'total':time.monotonic()-begin};m['window_ms']=window
  (self.out/(name+'.json')).write_text(json.dumps(m,indent=2))
  return name,started,frames,m
 def poll(self,window=8,save=True):
  for attempt in range(2):
   try:return self._poll_once(window,save)
   except (TimeoutError,ConnectionError,OSError):
    if attempt:raise
    self.connect()
 def _poll_once(self,window=8,save=True):
  from fast_reply import parse_fast
  begin=time.monotonic();self.check();checked=time.monotonic();started=time.time()
  raw=self.cmd(f'tx fast_poll {self.gain} 100 {window}',rb'^FAST_END[^\n]*\n',timeout=10)
  received=time.monotonic();name=f'{self.index:03d}';self.index+=1
  frames,m=parse_fast(raw,started)
  if save:
   (self.out/(name+'.log')).write_bytes(raw)
   (self.out/(name+'.decoded.json')).write_text(json.dumps(frames,indent=2))
  m['timing_seconds']={'check':checked-begin,'capture_decode_transfer':received-checked,'total':time.monotonic()-begin};m['window_ms']=window
  if save:(self.out/(name+'.json')).write_text(json.dumps(m,indent=2))
  else:(self.out/'monitor_latest.json').write_text(json.dumps(dict(metadata=m,frames=frames,poll_id=name)))
  if save:print(f'fast poll {name}: {len(frames)} CRC, decode {m.get("decode_us")} us, total {time.monotonic()-begin:.3f}s',flush=True)
  # Bound the interrogation rate even when the transport is now very fast.
  time.sleep(max(0,.15-(time.monotonic()-begin)))
  return name,started,frames,m
 def read_state(self,max_polls=None,expected=None):
  if getattr(self,'s',None) is not None and self.s.closed:self.connect()
  if max_polls is None:max_polls=18 if expected is not None else 12
  consensus=Consensus();misses=0;wide=False
  for attempt in range(max_polls):
   poll=self.poll(window=20 if wide else 8)
   recognized=any(parse_frame(frame) is not None for frame in poll[2])
   misses=0 if recognized else misses+1
   if misses>=4:wide=True
   state=consensus.add(*poll)
   if state and (expected is None or (state.get('mode','AUTO')=='AUTO' and state['setpoint_c']==expected)):return state
  raise RuntimeError('Consigne inconnue : aucun consensus frais après interrogations bornées')
 def button_once(self,command):
  if command not in ('plus','minus','manual','automatic'):raise ValueError(command)
  self.check()
  # v8 returns immediately after the release; fresh neutral polls confirm effect.
  raw=self.cmd(f'tx {command}_once {self.gain}',rb'^TX_DONE[^\n]*\n',timeout=10)
  (self.out/f'action_{self.index:03d}_{command}.log').write_bytes(b'\n'.join(x for x in raw.splitlines() if not x.startswith(b'd ')))
  if b'TX_DONE press_rc=0 release_rc=0' not in raw:raise RuntimeError('Émission incertaine; aucune répétition automatique')
 def step(self,command,before=None):
  began=time.monotonic()
  reused=not (getattr(self,'s',None) is not None and self.s.closed) and isinstance(before,dict) and isinstance(before.get('setpoint_c'),int) and not isinstance(before.get('setpoint_c'),bool) and isinstance(before.get('observed_at'),(int,float)) and 0<=time.time()-before['observed_at']<=10 and len(set(before.get('confirmed_by_polls',[])))>=2
  if not reused:
   try:before=self.read_state()
   except Exception as exc:raise PrecheckError('Commande non émise : lecture préalable impossible — '+str(exc)) from exc
  precheck_seconds=time.monotonic()-began
  if before.get('mode','AUTO')!='AUTO':raise PrecheckError('Commande température refusée hors mode automatique')
  target=before['setpoint_c']+(1 if command=='plus' else -1)
  if not 10<=target<=25:raise RuntimeError('Hors plage autorisée 10..25 °C')
  journal={'before':before,'command':command,'target':target,'result':'pending','sent_at':time.time(),'baseline_reused':reused,'precheck_seconds':precheck_seconds}
  path=self.out/f'command_{self.index:03d}.json';path.write_text(json.dumps(journal,indent=2))
  try:
   tx_start=time.monotonic();self.button_once(command);journal['transmit_seconds']=time.monotonic()-tx_start
   confirm_start=time.monotonic();after=self.read_state(expected=target);journal['confirmation_seconds']=time.monotonic()-confirm_start;journal['after']=after
   if after['setpoint_c']!=target:raise RuntimeError(f'Consigne reçue {after["setpoint_c"]}, attendue {target}; pas de répétition')
   journal['result']='confirmed_by_readback';return journal
  except Exception as exc:journal.update(result='indeterminate',error=str(exc));raise
  finally:journal['total_seconds']=time.monotonic()-began;path.write_text(json.dumps(journal,indent=2))

 def confirm_mode(self,mode,level=None,setting_menu=False):
  consensus=Consensus()
  for _ in range(20):
   poll=self.poll();state=consensus.add(*poll)
   if state and state.get('mode')==mode and (level is None or state.get('power_mode')==level) and (not setting_menu or state.get('display_context')=='setting_menu'):return state
  raise RuntimeError('Mode non confirmé ; aucune répétition automatique')
 def set_mode(self,target):
  if target not in ('AUTO','P1','P2','P3'):raise PrecheckError('Mode non autorisé')
  try:before=self.read_state()
  except Exception as exc:raise PrecheckError('Lecture préalable impossible : '+str(exc)) from exc
  state=before;sent=False;actions=[]
  if state.get('mode') not in ('AUTO','MANUAL'):raise PrecheckError('Réglage refusé pendant extinction ou état non confirmé')
  try:
   wanted='AUTO' if target=='AUTO' else 'MANUAL'
   if state['mode']!=wanted:
    sent=True;button='automatic' if wanted=='AUTO' else 'manual'
    self.button_once(button);actions.append(button);state=self.confirm_mode(wanted)
   if wanted=='MANUAL':
    level=int(target[1])
    for _ in range(2):
     if state['power_mode']==level:break
     # +/- changes power only while the M setting screen is freshly confirmed.
     # Reuse that confirmation immediately; extra reads can outlive the screen.
     if state.get('display_context')!='setting_menu' or not 0<=time.time()-state['observed_at']<=2:
      sent=True;self.button_once('manual');actions.append('manual')
      state=self.confirm_mode('MANUAL',setting_menu=True)
     if state['power_mode']==level:break
     if not 0<=time.time()-state['observed_at']<=2:raise RuntimeError('Écran de réglage expiré ; aucun +/- envoyé')
     step=1 if state['power_mode']<level else -1;button='plus' if step==1 else 'minus';sent=True
     self.button_once(button);actions.append(button);state=self.confirm_mode('MANUAL',state['power_mode']+step)
    if state['power_mode']!=level:raise RuntimeError('Puissance cible non atteinte')
   return dict(before=before,after=state,actions=actions)
  except Exception as exc:
   if not sent:raise PrecheckError(str(exc)) from exc
   raise

 def power_hold3s(self):
  self.check()
  raw=self.cmd('tx power_hold3s 10',rb'^(?:TX_DONE|POWER_REJECT)[^\n]*\n',timeout=10)
  (self.out/f'power_{time.time_ns()}.log').write_bytes(raw)
  if b'POWER_REJECT' in raw:raise PrecheckError('Power non émis : temporisation active')
  if b'TX_DONE press_rc=0 release_rc=0' not in raw:raise RuntimeError('Power incertain ; aucune répétition')
  m=re.search(rb'POWER_HOLD packets=(\d+) elapsed_ms=(\d+) planned_ms=3000 cadence_ms=64 rc=0',raw)
  if not m or not 1<=int(m[1])<=47 or not 3000<=int(m[2])<=3200:raise RuntimeError('Durée Power non validée ; aucune répétition')
  return dict(status='sent',hold_ms=int(m[2]),press_packets=int(m[1]),release_sent=True,power_state=None)
