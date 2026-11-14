from pathlib import Path
import sys,json,zlib,numpy as np
from scipy.ndimage import gaussian_filter1d
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'radio'))
from decode_cyrf import CODEBOOK,SOP_BITS,frame_crc
from iq_decode import decode_file
base=ROOT/'private/waveforms';base.mkdir(parents=True,exist_ok=True);header=[];report=[]
for name,payload in [('manual','1234882217c87e'),('automatic','1234822817c87d'),('manual_release','123400aa17c87e'),('automatic_release','123400aa17c87d')]:
 data=bytes.fromhex(payload);body=bytes([len(data)])+data;frame=body+frame_crc(body).to_bytes(2,'little')
 chips='11001100'*8+SOP_BITS+'1010'+SOP_BITS+'1'+''.join(''.join(str((CODEBOOK[b]>>i)&1)for i in range(32))for b in frame)+'1100'
 nrz=np.repeat(np.array([int(x)*2-1 for x in chips],float),40);freq=323200*gaussian_filter1d(nrz,.267*40,mode='nearest')+600
 sig=128*np.exp(2j*np.pi*np.cumsum(freq)/40000000);sig[:80]*=np.linspace(0,1,80);sig[-80:]*=np.linspace(1,0,80);sig=np.r_[np.zeros(80),sig,np.zeros(120)]
 iq=np.round(np.column_stack([sig.real,sig.imag])).astype('<i2');iq.tofile(base/(name+'.cs16'))
 meta=dict(fs=40000000,lo_mhz=2480,scale=1,sample_map=[[0,0,len(iq)]],continuous_verified=True,synthetic=True,payload_hex=payload,frame_hex=frame.hex())
 (base/(name+'.json')).write_text(json.dumps(meta))
 found=decode_file(base/(name+'.cs16'));assert any(f.get('crc_matches') and f['frame_hex']==frame.hex() for f in found),(name,found)
 words=((iq[:,0].astype(np.int32)&1023)|((iq[:,1].astype(np.int32)&1023)<<10)).astype('<u4');assert len(words)<=21384
 header.append('static const uint32_t wave_'+name+'[] = {\n'+',\n'.join(','.join('0x%05xu'%int(v)for v in words[i:i+12])for i in range(0,len(words),12))+'\n};\n#define CRC_'+name.upper()+' '+str(zlib.crc32(words.tobytes()))+'U\n')
 report.append(dict(name=name,frame=frame.hex(),samples=len(words),offline_decoded=True))
(ROOT/'radio/src/mode_waveforms.h').write_text('/* Offline generated M/A candidates; no Power waveform. */\n'+'\n'.join(header));(ROOT/'waveforms-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
