/* SPDX-License-Identifier: GPL-3.0-or-later
 * CRC-protected stop-and-wait output. Never retry RF.
 */
#include <zephyr/kernel.h>
#include <zephyr/multi_heap/shared_multi_heap.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/shell/shell.h>
#include <zephyr/random/random.h>
#include "../../nano33_gateway/link_protocol.h"
static const struct device *link_uart=DEVICE_DT_GET(DT_NODELABEL(uart1));
K_SEM_DEFINE(command_ready,0,1);
K_MUTEX_DEFINE(output_lock);
enum { FIFO_SIZE=32768 };
static uint8_t *fifo;static size_t head,tail,used;
static atomic_t busy,fault,radio_quiet,uart_active;
void ania_link_quiet(int enabled){
 atomic_set(&radio_quiet,enabled);
 if(enabled)while(atomic_get(&uart_active))k_sleep(K_MSEC(1));
}
static uint32_t boot,accepted,output_seq;
static size_t queued(void){k_mutex_lock(&output_lock,K_FOREVER);size_t n=used;k_mutex_unlock(&output_lock);return n;}
static char command[LINK_DATA+1];
static uint8_t tx[LINK_SIZE],rx[LINK_SIZE],pending[LINK_DATA];static uint8_t pending_len;
static int transport_init(const struct shell_transport *t,const void *cfg,shell_transport_handler_t h,void *ctx){return 0;}
static int transport_uninit(const struct shell_transport *t){return 0;}
static int transport_enable(const struct shell_transport *t,bool block){return 0;}
static int transport_read(const struct shell_transport *t,void *data,size_t n,size_t *got){*got=0;return 0;}
static int transport_write(const struct shell_transport *t,const void *data,size_t n,size_t *sent){
 const uint8_t *p=data;*sent=0;int64_t deadline=k_uptime_get()+5000;
 while(*sent<n){
  if(atomic_get(&fault)){*sent=n;return 0;}
  k_mutex_lock(&output_lock,K_FOREVER);
  size_t take=MIN(n-*sent,FIFO_SIZE-used);
  for(size_t i=0;i<take;i++){fifo[head]=p[*sent+i];head=(head+1)%FIFO_SIZE;}used+=take;
  k_mutex_unlock(&output_lock);*sent+=take;
  if(!take){if(k_uptime_get()>deadline){atomic_set(&fault,1);*sent=n;break;}k_sleep(K_MSEC(1));}
 }
 return 0;
}
static const struct shell_transport_api api={.init=transport_init,.uninit=transport_uninit,.enable=transport_enable,.read=transport_read,.write=transport_write};
static const struct shell_transport transport={.api=&api};
SHELL_DEFINE(link_shell,"",&transport,256,0,0);
void ania_spi_commands(void){
 struct shell_backend_config_flags flags=SHELL_DEFAULT_BACKEND_CONFIG_FLAGS;
 int rc=shell_init(&link_shell,NULL,flags,false,0);
 if(!rc)rc=shell_start(&link_shell);
 if(rc){atomic_set(&fault,1);return;}
 for(;;){k_sem_take(&command_ready,K_FOREVER);shell_execute_cmd(&link_shell,command);atomic_clear(&busy);}
}

/* UART uses existing MOSI wire as RX and MISO wire as TX. A valid frame is
 * required before any request is considered. CRC resynchronizes after loss. */
static void link_worker(void *a,void *b,void *c){
 if(!device_is_ready(link_uart)){printk("UART_LINK unavailable\n");return;}
 boot=sys_rand32_get();if(!boot)boot=1;
 size_t received=0;
 printk("UART_LINK ready=1 baud=230400 RX=D11 TX=D12 no_rf=1\n");
 for(;;){
  if(atomic_get(&radio_quiet)){k_sleep(K_MSEC(1));continue;}
  uint8_t ch;
  if(uart_poll_in(link_uart,&ch)){k_sleep(K_MSEC(1));continue;}
  rx[received++]=ch;
  if(received<LINK_SIZE)continue;
  if(!lvalid(rx)){memmove(rx,rx+1,LINK_SIZE-1);received=LINK_SIZE-1;continue;}
  for(;;){
   while(atomic_get(&radio_quiet))k_sleep(K_MSEC(1));
   atomic_set(&uart_active,1);
   if(!atomic_get(&radio_quiet))break;
   atomic_clear(&uart_active);
  }
  received=0;
  if(lget(rx+4)==boot){
   if(pending_len&&lget(rx+12)==output_seq)pending_len=0;
   if(lrequest_ok(rx,boot,accepted,atomic_get(&busy)||atomic_get(&fault)||queued()||pending_len)){
    memcpy(command,rx+20,rx[3]);command[rx[3]]=0;
    accepted=lget(rx+8);atomic_set(&busy,1);k_sem_give(&command_ready);
   }
  }
  if(!pending_len){
   k_mutex_lock(&output_lock,K_FOREVER);pending_len=MIN(used,LINK_DATA);
   for(unsigned i=0;i<pending_len;i++){pending[i]=fifo[tail];tail=(tail+1)%FIFO_SIZE;}used-=pending_len;
   k_mutex_unlock(&output_lock);if(pending_len)output_seq++;
  }
  memset(tx,0,sizeof(tx));tx[3]=pending_len;lput(tx+4,boot);lput(tx+8,output_seq);lput(tx+12,accepted);
  lput(tx+16,(atomic_get(&busy)||queued()||pending_len?LINK_BUSY:0)|(atomic_get(&fault)?LINK_FAULT:0));
  memcpy(tx+20,pending,pending_len);lseal(tx);
  for(unsigned i=0;i<LINK_SIZE;i++)uart_poll_out(link_uart,tx[i]);
  /* 64 bytes at 230400 baud: allow the TX FIFO to finish before RF. */
  k_sleep(K_MSEC(3));
  atomic_clear(&uart_active);
 }
}
K_THREAD_DEFINE(link_uart_id,2560,link_worker,NULL,NULL,NULL,-1,0,SYS_FOREVER_MS);
void ania_spi_start(void){
 fifo=shared_multi_heap_alloc(SMH_REG_ATTR_EXTERNAL,FIFO_SIZE);
 if(!fifo){atomic_set(&fault,1);return;}
 k_thread_cpu_pin(link_uart_id,0);k_thread_start(link_uart_id);
}
