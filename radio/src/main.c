/* SPDX-License-Identifier: GPL-3.0-or-later
 * Dual-board v12 radio endpoint. Captured waveforms preserved from v11.
 * Every sample-index gap is recorded; never conceal loss.
 */
#include <stdlib.h>
#include <esp_attr.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <zephyr/sys/base64.h>
#include <zephyr/sys/crc.h>
#include <zephyr/multi_heap/shared_multi_heap.h>
#include <esp_sdr/esp_sdr.h>
#include <esp_sdr/esp_sdr_ring.h>
#define MAX_PAIRS 2000000U
#define DECODE_PAIRS 80000U
static int16_t *iq;
static unsigned freq=2422;
static int ready;
static struct esp_sdr_ring_stats stats;
static int run_rc;
static size_t target,stored;
static unsigned bits=16,stride=1;
static uint64_t expected,first_index,gap_samples,first_sink_cycles;
static size_t first_sink_pairs;
static uint32_t gap_count,segments;
struct segment {uint64_t index;uint32_t stored,n;};
static struct segment map[16];
K_SEM_DEFINE(start,0,1);
K_SEM_DEFINE(done,0,1);
static void IRAM_ATTR __attribute__((optimize("O3"))) sink(void *user,const int16_t *i,const int16_t *q,size_t n,uint64_t index){
 if(stored>=target){esp_sdr_ring_stop();return;}
 if(stored && index!=expected){gap_count++;if(index>expected)gap_samples+=(index-expected+stride-1)/stride;}
 size_t skip=(stride-index%stride)%stride;
 if(skip>=n){expected=index+n;return;}
 size_t available=(n-skip+stride-1)/stride;
 size_t take=MIN(available,target-stored);uint64_t out_index=(index+skip)/stride;
 if(!stored){first_index=out_index;first_sink_cycles=k_cycle_get_64();first_sink_pairs=n;}
 int8_t *dest=(int8_t*)iq+stored*2;
 for(size_t k=0;k<take;k++){size_t j=skip+k*stride;dest[2*k]=(int8_t)(i[j]>>6);dest[2*k+1]=(int8_t)(q[j]>>6);}
 if(segments && out_index==map[segments-1].index+map[segments-1].n){map[segments-1].n+=take;}
 else if(segments<ARRAY_SIZE(map)){map[segments++]=(struct segment){out_index,stored,take};}
 else {esp_sdr_ring_stop();return;}
 stored+=take;expected=index+n;
 if(stored>=target)esp_sdr_ring_stop();
}
static void worker(void *a,void *b,void *c){
 for(;;){
  k_sem_take(&start,K_FOREVER);
  struct esp_sdr_ring_cfg cfg={.decim=4,.shift_fs4=true,.subsample=true,.sink=sink,.unit_pairs=12288};
  run_rc=esp_sdr_ring_run(&cfg,&stats);
  k_sem_give(&done);
 }
}
K_THREAD_DEFINE(worker_id,2560,worker,NULL,NULL,NULL,K_PRIO_COOP(1),0,SYS_FOREVER_MS);
static int status(const struct shell *s,size_t argc,char **argv){
 shell_print(s,"ANIA_RING ready=%d version=13 lo_mhz=%u fs=4000000 max_pairs=%u mode=RX_TX_MANUAL capture_variant=14 modes_variant=15 release_variant=18 passive_capture_ms=500",ready,freq,MAX_PAIRS);return 0;
}
static int acquire(unsigned ms,unsigned sample_bits,unsigned sample_stride){
 bits=sample_bits;stride=sample_stride;
 if(!ready || bits!=8 || stride!=1 || ms<1 || ms>500 || (uint64_t)ms*(4000/stride)>MAX_PAIRS)return -EINVAL;
 target=ms*(4000/stride);stored=0;expected=0;gap_samples=0;gap_count=0;segments=0;first_index=0;first_sink_cycles=0;first_sink_pairs=0;
 k_sem_give(&start);k_sem_take(&done,K_FOREVER);return run_rc;
}
static int dump_record(const struct shell *s){
 shell_print(s,"RING lo_mhz=%u apparent_center_mhz=%u fs=%u requested=%u stored=%u rc=%d status=%u lost_pairs=%u abandoned=%u elapsed_us=%llu gaps=%u gap_samples=%llu first_index=%llu segments=%u crc32=%u bits=%u scale=%u",freq,freq+4,4000000/stride,(unsigned)target,(unsigned)stored,run_rc,stats.status,stats.lost_pairs,stats.abandoned,stats.elapsed_us,gap_count,gap_samples,first_index,segments,crc32_ieee((uint8_t*)iq,stored*(bits/4)),bits,bits==16?16:1);
 for(unsigned j=0;j<segments;j++)shell_print(s,"M %llu %u %u",map[j].index,map[j].stored,map[j].n);
 const uint8_t *p=(uint8_t*)iq;
 for(size_t off=0;off<stored*(bits/4);off+=192){char out[257];size_t len;size_t n=MIN((size_t)192,stored*(bits/4)-off);int rc=base64_encode(out,sizeof(out),&len,p+off,n);if(rc)return rc;out[len]=0;shell_print(s,"d %s",out);}
 shell_print(s,"RING_END");return 0;
}
/* Fixed captured command waveforms. No transmission at boot or during check. */
#include <esp_sdr/esp_sdr_tx.h>
#include "waveforms.h"
#include "mode_waveforms.h"
#include "power_waveforms.h"
static int64_t power_next_ms;
#include "fast_decode.h"
extern uint32_t __esp_sdr_bank0_start[];
ESP_SDR_HIGH_BUF_DEFINE(uint32_t, tx_tail, [5000], 16);
static size_t tx_count;
static int tx_checked;
static float *decode_disc,*decode_chips;
static void stage_wave(const uint32_t *src,size_t n){
 tx_count=n;memcpy(__esp_sdr_bank0_start,src,MIN(n,16384U)*4);
 if(n>16384)memcpy(tx_tail,src+16384,(n-16384)*4);
}
static void IRAM_ATTR tx_gen(void *user,uint32_t *dst,uint64_t index,uint32_t n){
 while(n){
  uint32_t take;
  if(index>=tx_count){memset(dst,0,n*4);return;}
  if(index<16384){take=MIN(n,MIN((uint64_t)16384-index,tx_count-index));memcpy(dst,__esp_sdr_bank0_start+index,take*4);}
  else{take=MIN(n,tx_count-index);memcpy(dst,tx_tail+index-16384,take*4);}
  n-=take;index+=take;dst+=take;
 }
}
static int check_wave(const struct shell *s,const uint32_t *src,size_t n,const char *name,uint32_t expected_crc){
 if(n>21384)return -EINVAL;
 stage_wave(src,n);size_t cap;uint32_t *scratch=esp_sdr_tx_loop_buf(0,&cap);if(!scratch)return -ENOMEM;
 uint32_t max_us=0;for(size_t k=0;k<n;k+=16000){size_t take=MIN((size_t)16000,n-k);unsigned key=irq_lock();uint32_t t=k_cycle_get_32();tx_gen(NULL,scratch,k,take);uint32_t dt=k_cyc_to_us_floor32(k_cycle_get_32()-t);irq_unlock(key);max_us=MAX(max_us,dt);if(memcmp(scratch,src+k,take*4))return -EIO;}
 uint32_t crc=crc32_ieee((const uint8_t*)src,n*4);if(crc!=expected_crc || max_us>=300)return -EIO;
 shell_print(s,"WAVE_CHECK name=%s count=%u crc32=%u max_fill_us=%u no_rf=1",name,(unsigned)n,crc,max_us);return 0;
}
static int tx_check(const struct shell *s,size_t argc,char **argv){
 tx_checked=0;int rc=check_wave(s,wave_plus,ARRAY_SIZE(wave_plus),"plus",CRC_PLUS);if(!rc)rc=check_wave(s,wave_minus,ARRAY_SIZE(wave_minus),"minus",CRC_MINUS);if(!rc)rc=check_wave(s,wave_release,ARRAY_SIZE(wave_release),"release",CRC_RELEASE);if(!rc)rc=check_wave(s,wave_manual,ARRAY_SIZE(wave_manual),"manual",CRC_MANUAL);if(!rc)rc=check_wave(s,wave_automatic,ARRAY_SIZE(wave_automatic),"automatic",CRC_AUTOMATIC);if(!rc)rc=check_wave(s,wave_manual_release,ARRAY_SIZE(wave_manual_release),"manual_release",CRC_MANUAL_RELEASE);if(!rc)rc=check_wave(s,wave_automatic_release,ARRAY_SIZE(wave_automatic_release),"automatic_release",CRC_AUTOMATIC_RELEASE);if(!rc)rc=check_wave(s,wave_power,ARRAY_SIZE(wave_power),"power",CRC_POWER);if(!rc)rc=check_wave(s,wave_power_release,ARRAY_SIZE(wave_power_release),"power_release",CRC_POWER_RELEASE);tx_checked=rc==0;shell_print(s,"TX_CHECK rc=%d ready=%d no_rf=1",rc,tx_checked);return rc;
}
static int tx_one(const struct shell *s,const uint32_t *src,size_t n,const char *name){
 stage_wave(src,n);int rc=esp_sdr_tx_dac_play_gen(tx_gen,NULL,n);struct esp_sdr_tx_dac_stats st;esp_sdr_tx_dac_get_stats(&st);
 shell_print(s,"TX_PACKET name=%s rc=%d errors=%u restarts=%u fill_us_max=%u slack_us_min=%d elapsed_us=%u",name,rc,st.errors,st.restarts,st.fill_us_max,st.slack_us_min,st.elapsed_us);
 return rc?rc:(st.errors||st.restarts?-EIO:0);
}
static int tx_command_once(const struct shell *s,size_t argc,char **argv){
 const uint32_t *press=NULL,*release=wave_release;size_t press_n=0,release_n=ARRAY_SIZE(wave_release);const char *name=argv[0];
 if(!strcmp(name,"plus_once")){press=wave_plus;press_n=ARRAY_SIZE(wave_plus);}
 else if(!strcmp(name,"minus_once")){press=wave_minus;press_n=ARRAY_SIZE(wave_minus);}
 else if(!strcmp(name,"manual_once")){press=wave_manual;press_n=ARRAY_SIZE(wave_manual);release=wave_manual_release;release_n=ARRAY_SIZE(wave_manual_release);}
 else if(!strcmp(name,"automatic_once")){press=wave_automatic;press_n=ARRAY_SIZE(wave_automatic);release=wave_automatic_release;release_n=ARRAY_SIZE(wave_automatic_release);}
 else if(!strcmp(name,"power_hold3s")){if(k_uptime_get()<power_next_ms){shell_print(s,"POWER_REJECT cooldown_ms=%lld no_rf=1",(long long)(power_next_ms-k_uptime_get()));return -EAGAIN;}press=wave_power;press_n=ARRAY_SIZE(wave_power);release=wave_power_release;release_n=ARRAY_SIZE(wave_power_release);}
 else return -EINVAL;
 unsigned gain=argc>1?strtoul(argv[1],0,10):0;if(gain>12)return -EINVAL;
 if(!ready || !tx_checked)return -EACCES;
 tx_checked=0;
 if(!strcmp(name,"power_hold3s"))power_next_ms=k_uptime_get()+60000;
 /* Let the adjacent Wi-Fi bridge finish TCP acknowledgement before RF. */
 k_sleep(K_MSEC(30));
 int rc=esp_sdr_set_freq(2480);if(!rc)freq=2480;if(!rc)rc=esp_sdr_tx_set_gain(gain);
 if(rc){shell_print(s,"TX_PREFLIGHT rc=%d no_rf=1",rc);return rc;}
 unsigned packets=0;int64_t hold_start=k_uptime_get();
 if(!strcmp(name,"power_hold3s")){
  /* Experimental hold: fixed captured packet every 64 ms, for at most 3 s. */
  for(unsigned i=0;i<47;i++){
   int64_t wait=hold_start+(int64_t)i*64-k_uptime_get();if(wait>0)k_sleep(K_MSEC(wait));
   if(k_uptime_get()-hold_start>=3000)break;
   rc=tx_one(s,press,press_n,name);packets++;if(rc)break;
  }
  int64_t wait=hold_start+3000-k_uptime_get();if(!rc&&wait>0)k_sleep(K_MSEC(wait));
  shell_print(s,"POWER_HOLD packets=%u elapsed_ms=%lld planned_ms=3000 cadence_ms=64 rc=%d",packets,(long long)(k_uptime_get()-hold_start),rc);
 }else{if(!rc)rc=tx_one(s,press,press_n,name);k_sleep(K_MSEC(100));}
 /* Release is attempted even if any press waveform failed. */
 int release_rc=tx_one(s,release,release_n,"release");
 shell_print(s,"TX_DONE press_rc=%d release_rc=%d release_packets=1 gain_index=%u freq_mhz=2480",rc,release_rc,gain);
 return rc?rc:release_rc;
}
static int dump_fast(const struct shell *s){
 struct fast_frame frames[8];uint64_t start_cycles=k_cycle_get_64();
 bool continuous=stored==target&&!gap_count&&!stats.lost_pairs&&!run_rc&&segments==1;
 int count=continuous?fast_decode((const int8_t*)iq,stored,decode_disc,decode_chips,frames,ARRAY_SIZE(frames)):0;
 size_t stack_free=0;k_thread_stack_space_get(k_current_get(),&stack_free);
 uint32_t decode_us=k_cyc_to_us_floor64(k_cycle_get_64()-start_cycles),crc=0;
 shell_print(s,"FAST requested=%u stored=%u rc=%d lost_pairs=%u gaps=%u segments=%u continuous=%u decode_us=%u stack_free=%u count=%d",(unsigned)target,(unsigned)stored,run_rc,stats.lost_pairs,gap_count,segments,continuous,decode_us,(unsigned)stack_free,count);
 if(count>0)for(int i=0;i<count;i++){
  char hex[39];for(unsigned j=0;j<frames[i].len;j++){static const char digits[]="0123456789abcdef";hex[2*j]=digits[frames[i].raw[j]>>4];hex[2*j+1]=digits[frames[i].raw[j]&15];}hex[frames[i].len*2]=0;
  crc=crc32_ieee_update(crc,frames[i].raw,frames[i].len);
  shell_print(s,"F %u %u %s",frames[i].sample,frames[i].quality,hex);
 }
 shell_print(s,"FAST_END frames_crc32=%u",crc);return count<0?-ENOBUFS:0;
}
/* Neutral poll; no temperature button. RX starts before any USB output, same LO. */
static int poll_once(const struct shell *s,size_t argc,char **argv){
 unsigned gain=argc>1?strtoul(argv[1],0,10):8;unsigned settle=argc>2?strtoul(argv[2],0,10):100;unsigned window=argc>3?strtoul(argv[3],0,10):8;
 if((window!=8 && window!=20) || gain>12 || (settle!=100 && settle!=3000) || !ready || !tx_checked)return -EACCES;
 tx_checked=0;
 /* Let the adjacent Wi-Fi bridge finish TCP acknowledgement before RF. */
 k_sleep(K_MSEC(30));
 esp_sdr_set_turnaround(settle,settle==3000);
 int rc=esp_sdr_set_freq(2480);if(!rc)freq=2480;if(!rc)rc=esp_sdr_tx_set_gain(gain);if(rc)return rc;
 stage_wave(wave_release,ARRAY_SIZE(wave_release));
 rc=esp_sdr_tx_dac_play_gen(tx_gen,NULL,ARRAY_SIZE(wave_release));uint64_t tx_end=k_cycle_get_64();
 int rx_rc=acquire(window,8,1);
 struct esp_sdr_tx_dac_stats st;esp_sdr_tx_dac_get_stats(&st);
 uint64_t delivery=first_sink_cycles?k_cyc_to_us_floor64(first_sink_cycles-tx_end):0;
 shell_print(s,"POLL tx_rc=%d rx_rc=%d gain=%u tx_errors=%u tx_restarts=%u first_delivery_after_tx_us=%llu first_sink_pairs=%u rx_retuned=0 settle_us=%u",rc,rx_rc,gain,st.errors,st.restarts,delivery,(unsigned)first_sink_pairs,settle);
 if(!strcmp(argv[0],"fast_poll"))dump_fast(s);else dump_record(s);return rc?rc:rx_rc;
}
SHELL_STATIC_SUBCMD_SET_CREATE(tx_cmds,
 SHELL_CMD_ARG(power_hold3s,NULL,"Fixed 3s Power; 60s cooldown; explicit command only",tx_command_once,1,1),
 SHELL_CMD_ARG(manual_once,NULL,"One M press and release",tx_command_once,1,1),
 SHELL_CMD_ARG(automatic_once,NULL,"One A press and release",tx_command_once,1,1),
 SHELL_CMD_ARG(fast_poll,NULL,"Neutral poll decoded on ESP32",poll_once,1,3),
 SHELL_CMD_ARG(poll,NULL,"Neutral poll [gain 0..12] [settle 100|3000 us]",poll_once,1,3),
 SHELL_CMD(check,NULL,"Verify fixed waveforms and fill timing; no RF",tx_check),
 SHELL_CMD_ARG(plus_once,NULL,"One fixed + packet then release [gain 0..12]; requires check",tx_command_once,1,1),
 SHELL_CMD_ARG(minus_once,NULL,"One fixed - packet then release [gain 0..12]; requires check",tx_command_once,1,1),
 SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(tx,&tx_cmds,"Explicit bounded reproduction test",NULL);

/* Decode a long passive acquisition in overlapping, bounded scratch windows. */
static int dump_long_decoded(const struct shell *s){
 bool continuous=stored==target&&!gap_count&&!stats.lost_pairs&&!run_rc&&segments==1;
 shell_print(s,"LISTEN requested=%u stored=%u rc=%d lost_pairs=%u gaps=%u segments=%u continuous=%u tx_packets=0",(unsigned)target,(unsigned)stored,run_rc,stats.lost_pairs,gap_count,segments,continuous);
 uint32_t crc=0;unsigned total=0;int decode_error=0;
 if(continuous)for(size_t base=0;base<stored;base+=72000U){
  size_t n=MIN((size_t)DECODE_PAIRS,stored-base);struct fast_frame frames[8];
  int count=fast_decode((const int8_t*)iq+2*base,n,decode_disc,decode_chips,frames,ARRAY_SIZE(frames));
  if(count<0){decode_error=count;break;}
  for(int i=0;i<count;i++){
   char hex[39];static const char digits[]="0123456789abcdef";
   for(unsigned j=0;j<frames[i].len;j++){hex[2*j]=digits[frames[i].raw[j]>>4];hex[2*j+1]=digits[frames[i].raw[j]&15];}hex[frames[i].len*2]=0;
   crc=crc32_ieee_update(crc,frames[i].raw,frames[i].len);total++;
   shell_print(s,"L %u %u %s",(unsigned)base+frames[i].sample,frames[i].quality,hex);
  }
  if(base+n>=stored)break;
 }
 shell_print(s,"LISTEN_END frames_crc32=%u count=%u decode_error=%d",crc,total,decode_error);
 return continuous&&!decode_error?0:-EIO;
}

/* Passive bounded capture: no TX, no waveform check and no command replay. */
static int passive_capture(const struct shell *s,size_t argc,char **argv){
 if(argc!=2 || strcmp(argv[1],"500") || !ready)return -EINVAL;
 int rc=esp_sdr_set_freq(2480);if(rc)return rc;freq=2480;
 shell_print(s,"CAPTURE_ARMED delay_ms=2000 window_ms=500 tx_packets=0");
 /* A bounded arming delay allows a host cue; actual RX timing remains measured. */
 k_sleep(K_MSEC(2000));
 rc=acquire(500,8,1);
 shell_print(s,"PASSIVE tx_packets=0 window_ms=500 rc=%d",rc);
 int dump_rc=!strcmp(argv[0],"listen")?dump_long_decoded(s):dump_record(s);return rc?rc:dump_rc;
}
SHELL_STATIC_SUBCMD_SET_CREATE(rx_cmds,
 SHELL_CMD_ARG(listen,NULL,"Passive 500 ms decoded capture; no RF transmission",passive_capture,2,0),
 SHELL_CMD_ARG(capture,NULL,"Passive 500 ms IQ capture; no RF transmission",passive_capture,2,0),
 SHELL_CMD(status,NULL,"RX ring status",status),
 SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(rx,&rx_cmds,"RX-only continuous ring experiment",NULL);
int main(void){
 iq=shared_multi_heap_alloc(SMH_REG_ATTR_EXTERNAL,MAX_PAIRS*2);
 decode_disc=shared_multi_heap_alloc(SMH_REG_ATTR_EXTERNAL,DECODE_PAIRS*sizeof(float));
 decode_chips=shared_multi_heap_alloc(SMH_REG_ATTR_EXTERNAL,(DECODE_PAIRS/4+1)*sizeof(float));
 int rc=iq&&decode_disc&&decode_chips?esp_sdr_init():-ENOMEM;
 if(!rc)rc=esp_sdr_set_freq(freq);
 if(!rc)rc=esp_sdr_rx_set_lpf(ESP_SDR_RX_LPF_AUTO);
 k_thread_cpu_pin(worker_id,1);k_thread_start(worker_id);
 extern void ania_spi_start(void);extern void ania_spi_commands(void);
 ready=rc==0;ania_spi_start();printk("ANIA_RING version=13 init=%d RX_TX_MANUAL\n",rc);ania_spi_commands();return 0;
}
