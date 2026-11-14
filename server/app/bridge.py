#!/usr/bin/env python3
"""Authenticated local Ania bridge. Unsupported commands never reach the radio."""
import argparse, hashlib, hmac, json, os, sqlite3, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
CAPABILITIES={'plus':True,'minus':True,'setpoint_read':True,'setpoint_target':True,'on':False,'off':False,'P1':False,'P2':False,'P3':False,'power_state_read':False}
class Service:
 def __init__(self,radio,database):
  self.radio=radio;self.lock=threading.Lock();self.db_lock=threading.Lock();self.cache=None;self.last_known=None;self.target_thread=None
  self.command_gate=threading.Lock();self.command_pending=threading.Event();self.stop=threading.Event();self.monitor=None;self.consensus=None
  self.db=sqlite3.connect(database,check_same_thread=False)
  self.db.execute('CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, command TEXT NOT NULL, result TEXT NOT NULL)')
  for rid,c,payload in self.db.execute('SELECT id,command,result FROM commands').fetchall():
   if json.loads(payload).get('status')=='in_progress':self.save(rid,c,{'request_id':rid,'status':'indeterminate','error':'bridge restarted; command is never replayed'})
  self.db.commit()
 def save(self,rid,command,result):
  with self.db_lock:
   self.db.execute('INSERT OR REPLACE INTO commands VALUES (?,?,?)',(rid,command,json.dumps(result)));self.db.commit()
 def start_monitor(self):
  from state import Consensus
  self.consensus=Consensus()
  self.monitor=threading.Thread(target=self.watch,name='neutral-poll',daemon=True);self.monitor.start()
 def watch(self):
  while not self.stop.is_set():
   if not self.command_pending.is_set() and self.lock.acquire(False):
    try:
     if self.radio.s.closed:self.radio.connect()
     poll=self.radio.poll(save=False)
     self.observe_poll(poll)
    except Exception as exc:
     self.cache=None;self.consensus.samples.clear()
     print('Monitor unavailable:',str(exc),flush=True)
    finally:self.lock.release()
   self.stop.wait(.8)
 def observe_poll(self,poll):
  from state import parse_frame
  state=self.consensus.add(*poll)
  if state:
   if self.cache is None or state['observed_at']>=self.cache['observed_at']:
    self.cache=state;self.last_known=state
  elif self.cache:
   values={p['setpoint_c'] for frame in poll[2] if (p:=parse_frame(frame)) and p['kind']=='display'}
   # Silence is not a contradictory reading. Keep the actual timestamp unchanged.
   if any(value!=self.cache['setpoint_c'] for value in values) or time.time()-self.cache['observed_at']>10:self.cache=None
 def snapshot(self):
  state=self.cache
  if state and 0<=time.time()-state['observed_at']<=10:
   return 200,{'status':'confirmed','setpoint_c':state['setpoint_c'],'observed_at':state['observed_at'],'age_seconds':time.time()-state['observed_at'],'display_raw':state['display_raw'],'power_state':None,'power_mode':None}
  return None
 def unavailable(self,reason):
  state=self.last_known
  return 200,dict(status='stale' if state else 'unavailable',setpoint_c=state['setpoint_c'] if state else None,observed_at=state['observed_at'] if state else None,reason=reason,power_state=None,power_mode=None)
 def state(self):
  cached=self.snapshot()
  if cached:return cached
  if self.command_pending.is_set():return self.unavailable('Commande en cours')
  if not self.lock.acquire(timeout=.5):return self.unavailable('Reconnexion radio en cours')
  try:
   cached=self.snapshot()
   if cached:return cached
   state=self.radio.read_state(max_polls=6);self.cache=state;self.last_known=state
   if self.consensus is not None:self.consensus.samples.clear()
   return 200,{'status':'confirmed','setpoint_c':state['setpoint_c'],'observed_at':state['observed_at'],'age_seconds':time.time()-state['observed_at'],'display_raw':state['display_raw'],'power_state':None,'power_mode':None}
  except Exception as exc:
   self.cache=None
   return self.unavailable(str(exc))
  finally:self.lock.release()
 def command(self,data):
  command=data.get('command');rid=data.get('request_id')
  if command=='target':return self.target(data)
  if command not in ('plus','minus'):return 422,{'status':'unsupported','command':command}
  if not isinstance(rid,str) or not 16<=len(rid)<=100 or not all(c.isalnum()or c in '-_' for c in rid):return 400,{'status':'invalid_request_id'}
  if not self.command_gate.acquire(False):return 409,{'status':'busy','request_id':rid}
  self.command_pending.set()
  if not self.lock.acquire(timeout=2):
   self.command_pending.clear();self.command_gate.release();return 409,{'status':'busy','request_id':rid}
  try:
   with self.db_lock:existing=self.db.execute('SELECT command,result FROM commands WHERE id=?',(rid,)).fetchone()
   if existing:
    if existing[0]!=command:return 409,{'status':'request_id_conflict','request_id':rid}
    result=json.loads(existing[1]);result['duplicate']=True
    return (200 if result['status']=='confirmed' else 409),result
   self.save(rid,command,{'request_id':rid,'status':'in_progress'})
   try:
    before=self.cache;self.cache=None
    result=self.radio.step(command,before=before) if before is not None else self.radio.step(command)
    self.cache=result['after'];self.last_known=self.cache
    response={'request_id':rid,'status':'confirmed','command':command,'setpoint_c':result['after']['setpoint_c'],'observed_at':result['after']['observed_at'],'result':result}
    code=200
   except Exception as exc:
    response={'request_id':rid,'status':('not_sent' if getattr(exc,'command_sent',None) is False else 'indeterminate'),'command':command,'error':str(exc)};code=503
   self.save(rid,command,response);return code,response
  finally:
   if self.consensus is not None:self.consensus.samples.clear()
   self.lock.release();self.command_pending.clear();self.command_gate.release()
 def command_status(self,rid):
  with self.db_lock:row=self.db.execute('SELECT result FROM commands WHERE id=?',(rid,)).fetchone()
  return (200,json.loads(row[0])) if row else (404,{'status':'not_found'})
 def target(self,data):
  target=data.get('target_c');rid=data.get('request_id')
  if type(target) is not int or not 10<=target<=25:return 422,{'status':'invalid_target','error':'Consigne entière entre 10 et 25 °C'}
  if not isinstance(rid,str) or not 16<=len(rid)<=100 or not all(c.isalnum() or c in '-_' for c in rid):return 400,{'status':'invalid_request_id'}
  if not self.command_gate.acquire(False):return 409,{'status':'busy','request_id':rid}
  with self.db_lock:row=self.db.execute('SELECT command,result FROM commands WHERE id=?',(rid,)).fetchone()
  key='target:'+str(target)
  if row:
   self.command_gate.release()
   if row[0]!=key:return 409,{'status':'request_id_conflict','request_id':rid}
   return 200,dict(json.loads(row[1]),duplicate=True)
  self.command_pending.set()
  response=dict(request_id=rid,status='in_progress',target_c=target,steps_confirmed=0)
  self.save(rid,key,response)
  self.target_thread=threading.Thread(target=self.run_target,args=(rid,target,key),daemon=True)
  self.target_thread.start()
  return 202,response
 def run_target(self,rid,target,key):
  result=dict(request_id=rid,status='in_progress',target_c=target,steps_confirmed=0)
  acquired=False;sent=False;began=time.monotonic()
  try:
   acquired=self.lock.acquire(timeout=4)
   if not acquired:raise RuntimeError('Radio occupée, consigne non envoyée')
   # Always start a target sequence from a fresh independent radio reading.
   state=self.radio.read_state();self.cache=state;self.last_known=state
   result.update(setpoint_c=state['setpoint_c'],observed_at=state['observed_at'])
   self.save(rid,key,result)
   for _ in range(15):
    if state['setpoint_c']==target:break
    if self.stop.is_set() or time.monotonic()-began>120:raise RuntimeError('Séquence interrompue, aucune répétition automatique')
    direction='plus' if state['setpoint_c']<target else 'minus'
    self.cache=None;sent=True
    step=self.radio.step(direction,before=state)
    state=step['after'];self.cache=state;self.last_known=state
    result.update(setpoint_c=state['setpoint_c'],observed_at=state['observed_at'],steps_confirmed=result['steps_confirmed']+1)
    self.save(rid,key,result)
   if state['setpoint_c']!=target:raise RuntimeError('Cible non atteinte')
   result.update(status='confirmed',total_seconds=time.monotonic()-began)
  except Exception as exc:
   self.cache=None
   result.update(status='indeterminate' if sent else 'not_sent',error=str(exc),total_seconds=time.monotonic()-began)
  finally:
   self.save(rid,key,result)
   if acquired:
    if self.consensus is not None:self.consensus.samples.clear()
    self.lock.release()
   self.command_pending.clear();self.command_gate.release()
 def close(self):
  self.stop.set()
  if self.target_thread is not None:self.target_thread.join()
  if self.monitor is not None:self.monitor.join()
  self.radio.close();self.db.close()

def handler_for(service,token):
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,fmt,*args):pass
  def reply(self,code,data):
   raw=json.dumps(data).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def authorized(self):
   if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):self.reply(401,{'status':'unauthorized'});return False
   return True
  def do_GET(self):
   if not self.authorized():return
   if self.path=='/v1/capabilities':self.reply(200,{'firmware':int(os.environ.get('ANIA_FIRMWARE_VERSION','9')),'tx_gain_index':int(os.environ.get('ANIA_TX_GAIN','8')),'capabilities':CAPABILITIES});return
   if self.path.startswith('/v1/command/'):
    self.reply(*service.command_status(self.path.rsplit('/',1)[-1]));return
   if self.path=='/v1/state':self.reply(*service.state());return
   self.reply(404,{'status':'not_found'})
  def do_POST(self):
   if not self.authorized():return
   if self.path!='/v1/command':self.reply(404,{'status':'not_found'});return
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 1<=size<=2048:raise ValueError()
    self.connection.settimeout(5);data=json.loads(self.rfile.read(size))
    if not isinstance(data,dict):raise ValueError()
   except (ValueError,TimeoutError):self.reply(400,{'status':'invalid_json'});return
   self.reply(*service.command(data))
 return Handler

def main():
 p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=18766);p.add_argument('--token-file',type=Path,required=True);p.add_argument('--database',type=Path,required=True);p.add_argument('--radio-path',type=Path,default=Path(__file__).resolve().parent/'radio');a=p.parse_args()
 token=a.token_file.read_text().strip()
 if len(token)<32:raise SystemExit('Token must contain at least 32 characters')
 sys.path.insert(0,str(a.radio_path));from client import Radio
 service=Service(Radio(gain=int(os.environ.get("ANIA_TX_GAIN","8"))),str(a.database));server=ThreadingHTTPServer((a.host,a.port),handler_for(service,token));server.daemon_threads=False
 service.start_monitor()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close();service.close()
if __name__=='__main__':main()
