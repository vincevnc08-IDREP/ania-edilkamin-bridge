"""Render archived SDR-style views; input is derived data, not a live receiver."""
from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
P=Path(__file__).resolve().parents[1];d=np.load(P/'docs/data/radio_plot_data.npz');m=json.loads((P/'docs/data/radio_capture_metadata.json').read_text())
plt.rcParams.update({'figure.facecolor':'#111923','axes.facecolor':'#050a12','text.color':'#e9f3fc','axes.labelcolor':'#b7cad9','xtick.color':'#b7cad9','ytick.color':'#b7cad9','font.family':'DejaVu Sans','font.size':10,'savefig.facecolor':'#111923','svg.fonttype':'none'})
cmap=LinearSegmentedColormap.from_list('radio',['#01020d','#060d60','#0037bb','#00bfff','#fff23c','#ff5a00','#ffffff'])
fig=plt.figure(figsize=(13,9));gs=fig.add_gridspec(2,2,width_ratios=[1,.025],height_ratios=[1,2.1],left=.09,right=.92,bottom=.16,top=.85,hspace=.06,wspace=.04)
ax=fig.add_subplot(gs[0,0]);ax.plot(d['psd_freq_mhz'],d['psd_db'],color='#78e9ff',lw=.8);ax.fill_between(d['psd_freq_mhz'],d['psd_db'],-65,color='#48a6c5',alpha=.18);ax.set_ylim(-65,3);ax.set_xlim(-2,2);ax.set_ylabel('Spectre moyen\ndB relatifs');ax.grid(alpha=.15);ax.tick_params(labelbottom=False)
b=fig.add_subplot(gs[1,0],sharex=ax);im=b.pcolormesh(d['freq_mhz'],d['time_ms'],d['spectrogram_db'].T,cmap=cmap,vmin=-55,vmax=0,shading='auto',rasterized=True);b.set_ylim(8,0);b.set_ylabel('Temps depuis le début de capture (ms)');b.set_xlabel('Fréquence relative en bande de base (MHz)');b.axhline(float(d['sop_ms']),color='#79ffd4',lw=1,ls='--');b.text(-1.9,float(d['sop_ms'])-.13,'Début SOP d’une trame texte à CRC valide',fontsize=9,color='#79ffd4',bbox=dict(facecolor='#05131d',alpha=.8,edgecolor='none'))
c=fig.add_subplot(gs[1,1]);cb=fig.colorbar(im,cax=c);cb.set_label('dB relatifs au maximum du spectrogramme')
fig.text(.09,.94,'ANIA / RADIO EXPLORER',fontsize=24,fontweight='bold');fig.text(.09,.90,'CAPTURE ARCHIVÉE   ·   Réglage radio 2480 MHz   ·   I/Q 4 Méch/s   ·   Fenêtre 8 ms',color='#79ffd4',fontsize=11)
fig.text(.09,.055,'Vue inspirée des récepteurs SDR : spectre moyen en haut, cascade temporelle en dessous.\nDonnées réelles, sans calibration de puissance ; ce n’est ni du dBm ni une capture d’écran SDR++.\nSous-échantillonnage sans anti-repliement déclaré : spectre apparent, pas une mesure RF absolue.',color='#a9bdcc',fontsize=10)
for ext in ['png','svg']:fig.savefig(P/f'docs/assets/radio_waterfall.{ext}',dpi=170)
plt.close(fig)
fig,axes=plt.subplots(2,1,figsize=(12,7));fig.subplots_adjust(top=.83,bottom=.17,hspace=.55,left=.10,right=.94);fig.suptitle('ANIA / DU SIGNAL AU DÉCODAGE',fontsize=22,fontweight='bold',y=.96)
a=axes[0];a.plot(d['envelope_ms'],d['envelope_db'],color='#5ce3cb',lw=.8);a.axvline(float(d['sop_ms']),color='#ffd166',ls='--',label='SOP de la trame validée');a.set(xlabel='Temps (ms)',ylabel='Puissance moyenne\nrelative (dB)',xlim=(0,8));a.legend(facecolor='#172536',labelcolor='#e9f3fc',loc='upper left');a.grid(alpha=.15)
a=axes[1];a.plot(d['preamble_us'],d['phase_rad'],color='#75cfff',lw=.8);a.set(xlabel='Temps relatif au début du SOP (µs), délai du filtre compensé',ylabel='Écart de phase\n(rad / échantillon)',xlim=(0,120));a.grid(alpha=.15)
fig.text(.10,.045,'En haut : puissance I/Q moyennée sur 32 échantillons. En bas : discriminateur après FIR 65 coefficients.\nZoom limité aux 120 premières µs du préambule ; aucune charge utile publiée. CRC vérifié hors graphique.',fontsize=10,color='#a9bdcc')
for ext in ['png','svg']:fig.savefig(P/f'docs/assets/radio_timing.{ext}',dpi=170)
plt.close(fig)
