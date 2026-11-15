/* SPDX-License-Identifier: GPL-3.0-or-later
 * C port of the project's 4 Msps discriminator and CYRF hard/soft decoder.
 * No RF operations; emits only complete length-7/16 CRC-verified frames.
 */
#include "fast_decode.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "fast_filter.h"
#define SOP UINT64_C(0x17ff9e213690c782)
static const uint32_t pn[4]={0x0132be6f,0x012bf1db,0x02fa5ce3,0x02f99397};
static uint32_t code(unsigned b){unsigned r=b&31;uint32_t c=pn[(b>>5)&3];if(r)c=(c>>r)|(c<<(32-r));return c^(b<128?UINT32_MAX:0);}
static uint16_t crc(const uint8_t *p,size_t n){uint16_t c=0x2828;while(n--){c^=*p++;for(int j=0;j<8;j++)c=(c>>1)^((c&1)?0xa001:0);}return c^0xffff;}
static float median(float *v,unsigned n){for(unsigned i=1;i<n;i++){float x=v[i];unsigned j=i;while(j&&v[j-1]>x){v[j]=v[j-1];j--;}v[j]=x;}return n&1?v[n/2]:(v[n/2-1]+v[n/2])*.5f;}
static int attempt(const float *v,size_t n,int polarity,int soft,struct fast_frame *frame){
 if(n<165)return 0;
 float sign=polarity?-1.f:1.f,offset=0,bound=0;
 if(soft){
  float pos[128],neg[128],absolute[128];unsigned np=0,nn=0,na=0;
  for(unsigned block=0;block<2;block++)for(unsigned j=0;j<64;j++){
   float x=sign*v[block*68+j];if((SOP>>j)&1)pos[np++]=x;else neg[nn++]=x;
  }
  offset=(median(pos,np)+median(neg,nn))*.5f;
  for(unsigned block=0;block<2;block++)for(unsigned j=0;j<64;j++)absolute[na++]=fabsf(sign*v[block*68+j]-offset);
  bound=fmaxf(2*median(absolute,na),1e-6f);
 }
 for(unsigned block=0;block<2;block++){
  unsigned errors=0;for(unsigned j=0;j<64;j++)errors+=((sign*v[block*68+j]-offset>0)!=((SOP>>j)&1));
  if(errors>12)return 0;
 }
 unsigned count=0,wanted=19;int quality=1;
 for(size_t k=133;k+32<=n&&count<wanted;k+=32){
  uint32_t hard=0;float values[32];
  for(unsigned j=0;j<32;j++){float x=sign*v[k+j]-offset;if(x>0)hard|=UINT32_C(1)<<j;values[j]=fminf(bound,fmaxf(-bound,x));}
  unsigned best=0,besterr=33,second=33;float bestscore=-INFINITY;
  for(unsigned b=0;b<256;b++){
   uint32_t c=code(b);unsigned err=__builtin_popcount(c^hard);
   if(!soft){if(err<besterr){second=besterr;besterr=err;best=b;}else if(err<second)second=err;}
   else{float score=0;for(unsigned j=0;j<32;j++)score+=((c>>j)&1)?values[j]:-values[j];if(score>bestscore){bestscore=score;best=b;}}
  }
  if(soft){besterr=__builtin_popcount(code(best)^hard);for(unsigned b=0;b<256;b++)if(b!=best){unsigned e=__builtin_popcount(code(b)^hard);if(e<second)second=e;}}
  if(besterr>3||(int)second-(int)besterr<2)quality=0;
  frame->raw[count++]=best;
  if(count==1){if(best!=7&&best!=16)return 0;wanted=best+3;}
 }
 if(count!=wanted||crc(frame->raw,count-2)!=((unsigned)frame->raw[count-2]|(unsigned)frame->raw[count-1]<<8))return 0;
 frame->len=count;frame->quality=quality;return 1;
}
int fast_decode(const int8_t *iq,size_t n,float *disc,float *chips,struct fast_frame *out,size_t cap){
 if(n<800)return 0;
 float mi=0,mq=0;for(size_t k=0;k<n;k++){mi+=iq[2*k];mq+=iq[2*k+1];}mi/=n;mq/=n;
 float prev_i=0,prev_q=0;
 for(size_t k=0;k<n;k++){
  float fi=0,fq=0;
  if(k>=64){
   /* Symmetric FIR: pair taps to halve floating-point multiplications.
    * Steady-state sum(h)=1, so remove DC once after convolution. */
   for(unsigned j=0;j<32;j++){
    fi+=fir[j]*((int)iq[2*(k-j)]+(int)iq[2*(k-64+j)]);
    fq+=fir[j]*((int)iq[2*(k-j)+1]+(int)iq[2*(k-64+j)+1]);
   }
   fi+=fir[32]*iq[2*(k-32)];fq+=fir[32]*iq[2*(k-32)+1];fi-=mi;fq-=mq;
  }else for(unsigned j=0;j<=k;j++){fi+=fir[j]*(iq[2*(k-j)]-mi);fq+=fir[j]*(iq[2*(k-j)+1]-mq);}
  if(k)disc[k-1]=atan2f(fq*prev_i-fi*prev_q,fi*prev_i+fq*prev_q);
  prev_i=fi;prev_q=fq;
 }
 unsigned count=0;
 for(unsigned phase=0;phase<4;phase++){
  size_t length=(n-1-phase)/4;
  for(size_t k=0;k<length;k++){size_t p=phase+4*k;chips[k]=(disc[p]+disc[p+1]+disc[p+2]+disc[p+3])*.25f;}
  uint64_t bits=0;for(unsigned j=0;j<64;j++)if(chips[j]>0)bits|=UINT64_C(1)<<j;
  for(size_t k=0;k+165<=length;k++){
   unsigned errors=__builtin_popcountll(bits^SOP);int polarity=errors>=52;
   if(errors<=12||polarity){
    struct fast_frame frame;
    if(attempt(chips+k,length-k,polarity,0,&frame)||attempt(chips+k,length-k,polarity,1,&frame)){
     frame.sample=phase+4*k;int duplicate=0;
     for(unsigned i=0;i<count;i++)if(out[i].len==frame.len&&!memcmp(out[i].raw,frame.raw,frame.len)&&abs((int)out[i].sample-(int)frame.sample)<12){duplicate=1;break;}
     if(!duplicate){if(count>=cap)return -1;out[count++]=frame;}
    }
   }
   bits>>=1;if(chips[k+64]>0)bits|=UINT64_C(1)<<63;
  }
 }
 return count;
}
