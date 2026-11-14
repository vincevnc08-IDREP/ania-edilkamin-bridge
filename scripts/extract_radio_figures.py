"""Export only derived plot data from a local .cs16 capture (no payload/address)."""
from pathlib import Path
import argparse,json,sys,hashlib
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'radio'))
from iq_decode import decode_file
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads(a.capture.with_suffix('.json').read_text());fs=m['fs']
assert m['continuous_verified'] and m['gaps']==0 and len(m['sample_map'])==1
v=np.fromfile(a.capture,dtype='<i2').reshape(-1,2).astype(float);z=v[:,0]+1j*v[:,1];z-=z.mean()
frames=[r for r in decode_file(a.capture) if r.get('crc_matches') and r.get('length')==16]
assert frames,'A CRC-verified text frame is required'
r=frames[0];start=int(r['sop_native_sample']);window=z[max(0,start):start+int(.00012*fs)]
f,t,s=signal.spectrogram(z,fs=fs,nperseg=256,noverlap=224,return_onesided=False,mode='psd')
order=np.argsort(f);s=s[order];f=f[order];s_db=10*np.log10(np.maximum(s,1e-30)/s.max())
freq,psd=signal.welch(z,fs=fs,nperseg=1024,return_onesided=False);idx=np.argsort(freq);psd_db=10*np.log10(np.maximum(psd[idx],1e-30)/psd.max())
h=signal.firwin(65,650000,fs=fs);filtered=signal.lfilter(h,[1],z)
# The FIR group delay is retained in the time axis and corrected below.
fr=np.angle(filtered[1:]*filtered[:-1].conj());lo=start+32;hi=lo+int(.00012*fs)
power=np.mean(abs(z[:len(z)//32*32].reshape(-1,32))**2,axis=1);power_db=10*np.log10(np.maximum(power,1e-30)/power.max())
np.savez_compressed(ROOT/'docs/data/radio_plot_data.npz',envelope_ms=(np.arange(len(power))*32+15.5)/fs*1000,envelope_db=power_db,freq_mhz=f/1e6,time_ms=t*1000,spectrogram_db=s_db,psd_freq_mhz=freq[idx]/1e6,psd_db=psd_db,preamble_us=np.arange(hi-lo)/fs*1e6,phase_rad=fr[lo:hi],sop_ms=start/fs*1000)
meta={'source':'Capture historique après interrogation neutre, installation de référence','source_sha256':hashlib.sha256(a.capture.read_bytes()).hexdigest(),'samples':len(z),'sampling_hz':fs,'duration_ms':len(z)/fs*1000,'radio_tuning_mhz':m['lo_mhz'],'sample_gaps':m['gaps'],'quantization_bits':m['quantization_bits'],'crc_verified_text_frames':len(frames),'payload_bytes':r['length'],'sop_time_ms':start/fs*1000,'power_units':'dB relatifs au maximum de chaque graphique, pas des dBm','limitations':['Sous-échantillonnage déclaré sans filtre anti-repliement : spectre apparent non calibré.','Axe spectral relatif à la bande de base ; aucune conversion en fréquence RF absolue.','Signal seul insuffisant pour identifier un émetteur ; décodage et contexte utilisés.','Ni payload, ni adresse, ni horodatage personnel exportés.']}
(ROOT/'docs/data/radio_capture_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n');print('Exported',len(z),'samples summarized;',len(frames),'CRC-valid text frame(s)')
