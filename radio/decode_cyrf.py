"""Empirical CYRF6936 32-chip cyclic-code decoder; never transmits.
Default PN constants: Cypress CYRF6936 datasheet 38-16015 Rev G p29.
Mapping and +133 chip body alignment inferred from recorded IQ, not a published
8DR specification. CRC model: polynomial 0xa001, length included, seed
0x2828, final XOR 0xffff. Inferred from seven-byte frames and corroborated
by majority reconstruction of five sixteen-byte text responses. Actual
register contents have not been read; 0xd366 remains equivalent for 7-byte
payload-only CRC calculations.
"""
import argparse,json
from pathlib import Path
SOP=0x17ff9e213690c782
PN=(0x0132be6f,0x012bf1db,0x02fa5ce3,0x02f99397)
SOP_BITS=''.join(str((SOP>>i)&1) for i in range(64))
def encode_symbol(byte):
 c=PN[(byte>>5)&3];r=byte&31
 return (((c>>r)|(c<<(32-r)))&0xffffffff)^(0xffffffff if byte<128 else 0)
CODEBOOK=[encode_symbol(b)for b in range(256)]
def crc16(data,seed=0xd366):
 for b in data:
  seed^=b
  for _ in range(8):seed=(seed>>1)^(0xa001 if seed&1 else 0)
 return seed

def frame_crc(data):
 return crc16(data,0x2828)^0xffff

def decode_at(bits,k,polarity=0,max_errors=3):
 b=''.join(str(int(x)^polarity)for x in bits[k:])
 if len(b)<165:return None
 sop1=sum(x!=y for x,y in zip(b[:64],SOP_BITS))
 sop2=sum(x!=y for x,y in zip(b[68:132],SOP_BITS))
 if max(sop1,sop2)>5:return None
 symbols=[]
 for pos in range(133,len(b)-31,32):
  v=sum(int(x)<<i for i,x in enumerate(b[pos:pos+32]))
  distances=sorted(((v^c).bit_count(),n)for n,c in enumerate(CODEBOOK))
  d,n=distances[0];symbols.append({'byte':n,'errors':d,'margin':distances[1][0]-d})
  if len(symbols)>1 and len(symbols)>=symbols[0]['byte']+3:break
 if not symbols:return None
 n=symbols[0]['byte'];complete=len(symbols)==n+3;values=bytes(x['byte']for x in symbols)
 good=all(s['errors']<=max_errors and s['margin']>=2 for s in symbols)
 crc_matches=complete and frame_crc(values[:-2])==int.from_bytes(values[-2:],'little')
 valid=crc_matches and good
 return dict(sop_bit=k,polarity=polarity,sop_errors=[sop1,sop2],length=n,complete=complete,symbols=symbols,frame_hex=values.hex(),payload_hex=values[1:-2].hex() if complete else None,crc_equivalent_seed_valid=valid,crc_valid=valid,crc_matches=crc_matches,quality_pass=good,crc_seed='0x2828',crc_xorout='0xffff',crc_includes_length=True,crc_model_scope='inferred on 7-byte packets; corroborated by majority reconstruction of 16-byte text')

def detect(bits):
 positions=set()
 # <=5 errors imply at least one clean 8-bit chunk in each 64-bit SOP.
 for inv in (0,1):
  pat=''.join(str(int(x)^inv) for x in SOP_BITS)
  for off in range(0,64,8):
   start=0
   while True:
    hit=bits.find(pat[off:off+8],start)
    if hit<0:break
    if hit>=off:positions.add((hit-off,inv))
    start=hit+1
 result=[]
 for k,inv in sorted(positions):
  if len(bits)-k<165:continue
  d=sum(int(x)!=(int(y)^inv)for x,y in zip(bits[k:k+64],SOP_BITS))
  if d>5:continue
  match=decode_at(bits,k,inv)
  if match:result.append(match)
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('inputs',nargs='+',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();out=[]
 for path in a.inputs:
  try:rows=json.loads(path.read_text())
  except (ValueError,OSError):continue
  if not isinstance(rows,list):continue
  for row in rows:
   if not isinstance(row,dict):continue
   for e in row.get('events',[]):
    for m in detect(e.get('bits_1M','')):
     m.update(analysis=str(path.resolve()),file=row.get('file'),event_time_ms=e.get('radio_start_index',0)/4000,offset_hz=e.get('offset_hz'),duration_us=e.get('duration_us'));out.append(m)
  print(path.name,'cumulative',len(out),flush=True)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2));print('VALID',sum(x['crc_equivalent_seed_valid']for x in out),'TOTAL',len(out))
if __name__=='__main__':main()


def decode_soft_at(soft,k,polarity=0,max_errors=3):
 """Use discriminator confidence and SOP-based offset; CRC remains mandatory."""
 import numpy as np
 k=int(k)
 values=np.asarray(soft[k:],dtype=float)*(1 if not polarity else -1)
 if len(values)<165:return None
 known=np.array([int(x)*2-1 for x in SOP_BITS]*2)
 training=np.r_[values[:64],values[68:132]]
 offset=(np.median(training[known>0])+np.median(training[known<0]))/2
 values=values-offset
 b=''.join(map(str,(values>0).astype(int)))
 errors=[sum(x!=y for x,y in zip(b[a:a+64],SOP_BITS))for a in (0,68)]
 if max(errors)>5:return None
 code=np.array([[(c>>i&1)*2-1 for i in range(32)]for c in CODEBOOK])
 symbols=[]
 for pos in range(133,len(values)-31,32):
  v=values[pos:pos+32];bound=max(np.median(abs(training-offset))*2,1e-6);scores=code@np.clip(v,-bound,bound);order=np.argsort(scores);n=int(order[-1]);hard=(v>0)*2-1;hd=np.sum(code!=hard,axis=1);d=int(hd[n]);margin=int(np.min(np.delete(hd,n)))-d
  symbols.append(dict(byte=n,errors=d,margin=margin,soft_margin=float(scores[order[-1]]-scores[order[-2]])))
  if len(symbols)>=symbols[0]['byte']+3:break
 if not symbols:return None
 n=symbols[0]['byte'];complete=len(symbols)==n+3;raw=bytes(s['byte']for s in symbols);good=all(s['errors']<=max_errors and s['margin']>=2 for s in symbols);matches=complete and frame_crc(raw[:-2])==int.from_bytes(raw[-2:],'little')
 return dict(sop_bit=k,polarity=polarity,sop_errors=errors,length=n,complete=complete,symbols=symbols,frame_hex=raw.hex(),payload_hex=raw[1:-2].hex()if complete else None,crc_equivalent_seed_valid=matches and good,crc_valid=matches and good,crc_matches=matches,quality_pass=good,crc_seed='0x2828',crc_xorout='0xffff',crc_includes_length=True,decoder='soft_correlation',discriminator_offset=float(offset))


def frame_rank(r):
 return (not r['crc_matches'],not r['quality_pass'],sum(s['errors']for s in r['symbols'])+sum(r['sop_errors']))
