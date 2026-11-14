"""Validation indépendante des réponses et consensus de consigne, sans HA."""
import re, time, sys
from pathlib import Path
from decode_cyrf import frame_crc

def parse_frame(frame):
    try: raw=bytes.fromhex(frame['frame_hex'])
    except (KeyError, ValueError, TypeError): return None
    if len(raw)<3 or len(raw)!=raw[0]+3 or frame_crc(raw[:-2])!=int.from_bytes(raw[-2:],'little'): return None
    if not frame.get('continuous_verified'): return None
    payload=raw[1:-2]
    result={'raw_hex':raw.hex(),'quality_pass':bool(frame.get('quality_pass'))}
    match=re.fullmatch(rb'reg[ .](\d{2})&C([ -~]{8})',payload)
    if match:
        result.update(kind='display',mode='AUTO',power_mode=None,setpoint_c=int(match[1]),display_raw=payload.decode('ascii'),tail_raw=match[2].decode('ascii'))
    elif (match:=re.fullmatch(rb'Power [ .]([123])([ -~]{8})',payload)):
        result.update(kind='display',mode='MANUAL',power_mode=int(match[1]),setpoint_c=None,display_raw=payload.decode('ascii'))
    elif (match:=re.fullmatch(rb'Auto reg(\d{2}) &C +',payload)) and len(payload)==16:
        result.update(kind='display',mode='AUTO',power_mode=None,setpoint_c=int(match[1]),display_raw=payload.decode('ascii'),display_context='setting_menu')
    elif (match:=re.fullmatch(rb'POWER P([123]) +\+/- +',payload)) and len(payload)==16:
        result.update(kind='display',mode='MANUAL',power_mode=int(match[1]),setpoint_c=None,display_raw=payload.decode('ascii'),display_context='setting_menu')
    elif len(payload)==16 and re.fullmatch(rb'OFF +[0-9]+ *',payload):
        result.update(kind='display',mode='SHUTDOWN',power_mode=None,setpoint_c=None,shutdown_counter=int(payload.decode().split()[1]),display_raw=payload.decode('ascii'))
    elif len(payload)==16 and payload.strip()==b'OFF':
        result.update(kind='display',mode='OFF_DISPLAY',power_mode=None,setpoint_c=None,display_raw=payload.decode('ascii'))
    elif len(payload)==16 and all(32<=b<=126 for b in payload):
        result.update(kind='display_unparsed',display_raw=payload.decode('ascii'),power_state='unknown')
    elif len(payload)==7 and payload[:2]==bytes.fromhex('00ff'):
        result.update(kind='binary',payload_hex=payload.hex(),bytes=list(payload),power_state='unknown')
    else:return None
    return result

def state_key(state):
    return (state.get('mode','AUTO'),state.get('setpoint_c'),state.get('power_mode'))

class Consensus:
    """Two distinct polls agreeing, each <=30 s old; conflicts invalidate consensus."""
    def __init__(self): self.samples={}
    def add(self,poll_id,started,frames,metadata,now=None):
        now=time.time() if now is None else now
        self.samples={k:v for k,v in self.samples.items() if 0<=now-v['observed_at']<=30}
        if not metadata.get('continuous_verified') or not metadata.get('neutral_poll'): return self.current(now)
        if any(metadata.get(k)!=0 for k in ('tx_rc','rx_rc','tx_errors','tx_restarts')):return self.current(now)
        displays=[p for f in frames if (p:=parse_frame(f)) and p['kind']=='display']
        if not 0<=now-started<=30:return self.current(now)
        if len({state_key(p) for p in displays})>1:self.samples.clear();return None
        if displays:
            p=displays[0]
            if any(state_key(v)!=state_key(p) for v in self.samples.values()):self.samples.clear()
            self.samples[poll_id]=dict(p,observed_at=started,poll_id=poll_id)
        return self.current(now)
    def current(self,now=None):
        now=time.time() if now is None else now
        valid=[v for v in self.samples.values() if 0<=now-v['observed_at']<=30]
        if len(valid)<2:return None
        return dict(valid[-1],confirmed_by_polls=[v['poll_id'] for v in valid],age_seconds=now-valid[-1]['observed_at'])
