#!/usr/bin/env python3
"""Single-shot bridge requests. No retries, shared lock for reads and commands."""
import re, datetime, fcntl, json, math, os, pathlib, sys, time, urllib.request, urllib.error, uuid
ROOT = pathlib.Path(os.environ.get('ANIA_CONFIG_DIR', '/config'))
BASE = os.environ.get('ANIA_BRIDGE_URL') or ((ROOT/'ania_bridge.url').read_text().strip() if (ROOT/'ania_bridge.url').exists() else 'http://127.0.0.1:18766')

def unavailable(reason):
    return {'status':'unavailable','setpoint_c':None,'observed_at':None,'reason':reason}

def normalize(data):
    if data.get('status') == 'in_progress':return {k:data[k] for k in ('status','request_id','target_c','steps_confirmed','setpoint_c','observed_at') if k in data}
    if data.get('status') == 'stale':
        return {'status':'stale','setpoint_c':data.get('setpoint_c'),'observed_epoch':data.get('observed_at'),'observed_at':datetime.datetime.fromtimestamp(data['observed_at'],datetime.timezone.utc).isoformat() if data.get('observed_at') else None,'reason':data.get('reason','Reconnexion radio')}
    if data.get('status') != 'confirmed':
        return {'status':data.get('status','unavailable'),'setpoint_c':None,'observed_at':None,'reason':str(data.get('error',data.get('status','invalid_response')))[:240]}
    value, stamp = data.get('setpoint_c'), data.get('observed_at')
    if isinstance(value, bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
        raise ValueError('Invalid setpoint')
    if not isinstance(stamp,(float,int)) or not math.isfinite(stamp) or not -5 <= time.time()-stamp <= 90:
        raise ValueError('Invalid or stale reading')
    return {'status':'confirmed','setpoint_c':value,'observed_at':datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc).isoformat(), 'observed_epoch':stamp}

def request(path, payload=None):
    token=(ROOT/'ania_bridge.token').read_text().strip()
    req=urllib.request.Request(BASE+path, data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    # urllib does not replay failed requests; redirects are prohibited for credentials/commands.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=45 if payload else 30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (409,422,503):return json.load(exc)
        raise

def run(mode, argument=None):
    if mode=='status':
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}",argument or ""):return 2,unavailable("invalid_request_id")
        try:return 0,normalize(request("/v1/command/"+argument))
        except Exception as exc:return 1,unavailable(type(exc).__name__)
    if mode=='target':
        try:
            target=int(argument)
            if str(target)!=argument or not 10<=target<=25:raise ValueError()
        except (TypeError,ValueError):return 2,unavailable("invalid_target")
    if mode not in ('read','plus','minus','target'): return 2, unavailable('unsupported')
    cache=ROOT/'.ania_last_reading.json'
    with (ROOT/'.ania_radio.lock').open('a') as lock:
        deadline=time.monotonic()+(8 if mode!='read' else 0)
        while True:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:return (0 if mode=='read' else 1), {'status':'not_sent' if mode!='read' else 'busy','setpoint_c':None,'observed_at':None,'reason':'Lecture radio en cours; commande non émise'}
                time.sleep(.1)
        try:
            if mode=='read':
                try:
                    previous=json.loads(cache.read_text())
                    if previous.get('status')=='confirmed' and 0<=time.time()-previous.get('observed_epoch',0)<5:
                        return 0,previous
                except (OSError,ValueError,TypeError): pass
                data=normalize(request('/v1/state'))
            else:
                # Persist intent before sending. Never replay an interrupted operation.
                intent={'command':mode,'request_id':str(uuid.uuid4()),'created_at':time.time()}
                if mode=='target':intent['target_c']=target
                (ROOT/'.ania_last_intent.json').write_text(json.dumps(intent))
                data=normalize(request('/v1/command',{k:v for k,v in intent.items() if k!='created_at'}))
        except Exception as exc:
            # Never print response bodies, URLs with secrets, or Authorization headers.
            data=unavailable(type(exc).__name__)
        good=ROOT/'.ania_last_confirmed.json'
        if data['status']=='confirmed':good.write_text(json.dumps(data))
        elif mode=='read' and data.get('setpoint_c') is None:
            try:
                previous=json.loads(good.read_text())
                if 0<=time.time()-previous.get('observed_epoch',0)<=86400:
                    data=dict(previous,status='stale',reason='Lecture radio en cours de rétablissement')
            except (OSError,ValueError,TypeError):pass
        if data['status']!='in_progress':cache.write_text(json.dumps(data))
        return (0 if mode=='read' or data['status'] in ('confirmed','in_progress') else 1),data

if __name__=='__main__':
    code,data=run(sys.argv[1] if len(sys.argv) in (2,3) else '',sys.argv[2] if len(sys.argv)==3 else None)
    print(json.dumps(data));sys.exit(code)
