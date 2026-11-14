"""Strict parser for ESP32-decoded frames; CRC independently recomputed here."""
import re,zlib
from decode_cyrf import frame_crc

def parse_fast(raw,started):
 lines=raw.splitlines()
 def fields(prefix):
  selected=[line for line in lines if line.startswith(prefix)]
  if len(selected)!=1:raise ValueError('Missing or duplicate fast metadata')
  return {k.decode():int(v)for k,v in re.findall(rb'(\w+)=(-?\d+)',selected[0])}
 m=fields(b'FAST ');m.update(fields(b'POLL '));end=fields(b'FAST_END ')
 if not 0<=m.get('count',-1)<=8:raise ValueError('Decoder overflow or invalid count')
 continuous=(m.get('continuous')==1 and m.get('stored')==m.get('requested') and m.get('stored') in (32000,80000) and m.get('gaps')==0 and m.get('lost_pairs')==0 and m.get('rc')==0 and m.get('segments')==1)
 frames=[];all_raw=bytearray()
 for line in lines:
  if not line.startswith(b'F '):continue
  match=re.fullmatch(rb'F (\d+) ([01]) ([0-9a-f]+)',line)
  if not match:raise ValueError('Malformed decoded frame')
  packet=bytes.fromhex(match[3].decode());sample=int(match[1]);quality=match[2]==b'1'
  if len(packet) not in (10,19) or len(packet)!=packet[0]+3 or frame_crc(packet[:-2])!=int.from_bytes(packet[-2:],'little'):raise ValueError('Independent radio CRC verification failed')
  if not 0<=sample<m['stored']:raise ValueError('Invalid sample offset')
  frames.append({'frame_hex':packet.hex(),'crc_matches':True,'quality_pass':quality,'continuous_verified':continuous,'source':'ESP32 C decoder; server CRC rechecked','sop_native_sample':sample,'time_ms':(sample-32)/4000})
  all_raw.extend(packet)
 if len(frames)!=m['count'] or zlib.crc32(all_raw)!=end.get('frames_crc32'):raise ValueError('Incomplete or corrupted decoded response')
 m.update(continuous_verified=continuous,host_poll_time_unix=started,neutral_poll=True,embedded_decode=True)
 return frames,m
