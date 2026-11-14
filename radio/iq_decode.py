"""Reusable IQ decoder: same candidates and ranking as the v7 offline decoder."""
from pathlib import Path
import sys,json,numpy as np
from scipy import signal
from decode_cyrf_sensitive import SOP_BITS,decode_at,decode_soft_at,frame_rank
pat=np.array([int(x)*2-1 for x in SOP_BITS],dtype=np.int16)
def decode_file(path,offsets='0'):
 m=json.loads(path.with_suffix('.json').read_text());fs=m['fs'];v=np.fromfile(path,dtype='<i2').reshape(-1,2).astype(float);z=v[:,0]+1j*v[:,1];z-=z.mean();found=[]
 for index,stored,n in m['sample_map']:
  for offset in map(float,offsets.split(',')):
   h=signal.firwin(65,650000,fs=fs);y=signal.lfilter(h,[1],z[stored:stored+n]*np.exp(-2j*np.pi*offset*np.arange(n)/fs))
   y=signal.resample_poly(y,4000000//int(np.gcd(4000000,fs)),fs//int(np.gcd(4000000,fs)));fr=np.angle(y[1:]*y[:-1].conj());
   for phase in range(4):
    length=(len(fr)-phase)//4;soft=fr[phase:phase+length*4].reshape(-1,4).mean(axis=1);hard=(soft>0).astype(np.int16)*2-1
    corr=signal.correlate(hard,pat,mode='valid',method='direct');hits=np.flatnonzero(abs(corr)>=44)
    for k in hits:
     bits=''.join(map(str,(hard[k:k+10000]>0).astype(int)));hard_result=decode_at(bits,0,int(corr[k]<0));soft_result=decode_soft_at(soft,k,int(corr[k]<0));candidates=[r for r in (hard_result,soft_result)if r];r=min(candidates,key=frame_rank) if candidates else None
     if r:
      r.update(file=str(path.resolve()),source_segment_stored=stored,source_segment_index=index,sop_native_sample=stored+(phase+k*4)*fs/4000000-32,offset_hz=offset,phase=phase,time_ms=(index/fs+(phase+k*4)/4e6-32/fs)*1000,lo_mhz=m['lo_mhz'],source='continuous IQ all phases',continuous_verified=m['continuous_verified']);found.append(r)
 # Prefer verified and fewest corrections among same-time phase/offset detections.
 dedup=[]
 for r in sorted(found,key=frame_rank):
  if not any(abs(r['time_ms']-t['time_ms'])<.003 for t in dedup):dedup.append(r)
 return sorted(dedup,key=lambda r:r['time_ms'])
