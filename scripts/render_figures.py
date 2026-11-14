"""Regenerate documentation figures: pip install matplotlib numpy."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path(__file__).resolve().parents[1];OUT=P/'docs/assets'
BG='#101d2c';FG='#ecf4ff';MUTED='#a9bdcc';TEAL='#5ce3cb';GOLD='#ffd166'
plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'text.color':FG,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,'font.family':'DejaVu Sans','font.size':11,'savefig.facecolor':BG,'svg.fonttype':'none'})
def save(fig,name):
 fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');fig.savefig(OUT/(name+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)
def clean(ax):
 for s in ax.spines.values():s.set_visible(False)
 ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True)
rows=json.loads((P/'docs/data/gain_trials.json').read_text());target=json.loads((P/'docs/data/target_trials.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(12,5.4));fig.subplots_adjust(bottom=.25,wspace=.3,top=.78)
fig.suptitle('MESURES RÉELLES · UNE INSTALLATION',fontsize=19,fontweight='bold',y=.98)
a=axes[0];values=[r for r in target if r['steps_confirmed']==1];v=[r['total_seconds'] for r in values];labels=[f'Cible {r["target_c"]} °C' for r in values];a.bar(labels,v,color=TEAL,width=.5);a.set_ylim(0,4.2);a.set_ylabel('Durée jusqu’à confirmation (secondes)');a.set_title('Deux changements d’un degré',loc='left',pad=18)
for i,t in enumerate(v):a.text(i,t+.12,f'{t:.3f} s',ha='center',fontweight='bold',color=TEAL)
clean(a)
a=axes[1];gains=[8,10,12];counts=[sum(r['frames']>0 for r in rows if r['gain']==g) for g in gains];n=[sum(r['gain']==g for r in rows) for g in gains];a.bar([str(g) for g in gains],counts,color=[MUTED,TEAL,MUTED],width=.55);a.set_ylim(0,20);a.set_yticks([0,6,12,18]);a.set_ylabel('Interrogations avec au moins une trame');a.set_xlabel('Indice de gain logiciel — pas des dBm');a.set_title('Réception selon le gain',loc='left',pad=18)
for i,(c,total) in enumerate(zip(counts,n)):a.text(i,c+.5,f'{c}/{total}',ha='center',fontweight='bold')
clean(a);fig.text(.07,.07,'Échantillons courts, contexte RF unique. Une trame reçue ne signifie pas une consigne confirmée.\nLes lectures du cache HTTP ne sont pas comptées comme des commandes radio.',fontsize=10,color=MUTED);save(fig,'mesures')
fig,ax=plt.subplots(figsize=(13,4.6));ax.set_xlim(0,13);ax.set_ylim(0,4.6);ax.axis('off');ax.text(.25,4.12,'ANIA / ARCHITECTURE',fontsize=23,fontweight='bold');ax.text(.25,3.65,'Deux cartes, deux rôles · un état confirmé de bout en bout',color=MUTED,fontsize=12)
boxes=[('Home\nAssistant','Carte + consigne'),('Serveur\nPython','API + déduplication'),('Nano\n33 IoT','Wi-Fi réseau'),('Nano\nESP32','Radio SDR'),('Poêle\nAnia','Réponse observée')]
for i,(title,sub) in enumerate(boxes):
 x=.25+i*2.6;ax.add_patch(FancyBboxPatch((x,1.4),2.05,1.55,boxstyle='round,pad=.08,rounding_size=.15',facecolor='#20364b',edgecolor=TEAL if i in [2,3] else '#40566a',linewidth=1.4));ax.text(x+1.025,2.37,title,ha='center',va='center',fontsize=15,fontweight='bold');ax.text(x+1.025,1.65,sub,ha='center',fontsize=9,color=MUTED)
 if i<4:
  ax.annotate('',(x+2.52,2.15),(x+2.15,2.15),arrowprops=dict(arrowstyle='<->',color=TEAL,lw=1.7));ax.text(x+2.34,1.08,['HTTP LAN','TCP Wi-Fi','SPI','2480 MHz'][i],ha='center',fontsize=9,color=GOLD)
ax.text(.25,.3,'Les modes marche/arrêt et P1/P2/P3 restent hors périmètre validé.',color=MUTED);save(fig,'architecture')
fig,ax=plt.subplots(figsize=(10,6));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off');ax.text(.3,5.55,'EMPILAGE / CONTACTS À CONSERVER',fontsize=19,fontweight='bold');ax.text(.3,5.05,'Schéma fonctionnel — ce n’est pas une vue de repérage physique des broches.',color=MUTED,fontsize=10)
for x,title in [(1,'Nano 33 IoT · dessous'),(6.2,'Nano ESP32 · dessus')]:
 ax.add_patch(FancyBboxPatch((x,.6),2.8,3.9,boxstyle='round,pad=.1',facecolor='#20364b',edgecolor=TEAL));ax.text(x+1.4,4.1,title,ha='center',fontweight='bold',fontsize=11)
for i,(label,role) in enumerate([('D10','CS'),('D11','MOSI'),('D12','MISO'),('D13','SCK'),('D2','READY'),('GND ×2','Masse'),('VIN','Alimentation*')]):
 y=3.6-i*.4;ax.plot([3.8,6.1],[y,y],color=TEAL,lw=1.4);ax.text(2.4,y,label,ha='center',va='center',fontsize=10);ax.text(7.6,y,label,ha='center',va='center',fontsize=10);ax.text(4.95,y+.07,role,ha='center',fontsize=9,color=GOLD)
ax.text(.3,.12,'* Vérifier les révisions et le chemin d’alimentation. Tous les autres contacts restent séparés.',fontsize=10,color=MUTED);save(fig,'liaison')
