/* SPDX-License-Identifier: GPL-3.0-or-later
 * CRC-protected stop-and-wait output. Never retry RF.
 */
#include <zephyr/kernel.h>
#include <zephyr/multi_heap/shared_multi_heap.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/shell/shell.h>
#include <zephyr/random/random.h>
#include "../../nano33_gateway/link_protocol.h"
static const struct device *spi=DEVICE_DT_GET(DT_NODELABEL(spi2));
static const struct device *gpio=DEVICE_DT_GET(DT_NODELABEL(gpio0));
static const struct spi_config config={.frequency=2000000,.operation=SPI_OP_MODE_PERIPHERAL|SPI_WORD_SET(8)};
K_SEM_DEFINE(transferred,0,1);
K_SEM_DEFINE(command_ready,0,1);
K_MUTEX_DEFINE(output_lock);
enum { FIFO_SIZE=32768 };
static uint8_t *fifo;static size_t head,tail,used;
static atomic_t busy,fault;
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

static void complete(const struct device *dev,int result,void *arg){
 gpio_pin_set(gpio,5,0);if(result<0)atomic_set(&fault,1);k_sem_give(&transferred);
}
static void link_worker(void *a,void *b,void *c){
 if(!device_is_ready(spi)||!device_is_ready(gpio)){printk("SPI_LINK device unavailable\n");return;}
 gpio_pin_configure(gpio,5,GPIO_OUTPUT_INACTIVE);
 boot=sys_rand32_get();if(!boot)boot=1;

 struct spi_buf tb={tx,sizeof(tx)},rb={rx,sizeof(rx)};
 struct spi_buf_set ts={&tb,1},rs={&rb,1};
 for(;;){
  if(!pending_len){k_mutex_lock(&output_lock,K_FOREVER);pending_len=MIN(used,LINK_DATA);
   for(unsigned i=0;i<pending_len;i++){pending[i]=fifo[tail];tail=(tail+1)%FIFO_SIZE;}used-=pending_len;
   k_mutex_unlock(&output_lock);if(pending_len)output_seq++;
  }
  memset(tx,0,sizeof(tx));tx[3]=pending_len;lput(tx+4,boot);lput(tx+8,output_seq);lput(tx+12,accepted);
  lput(tx+16,(atomic_get(&busy)||queued()||pending_len?LINK_BUSY:0)|(atomic_get(&fault)?LINK_FAULT:0));memcpy(tx+20,pending,pending_len);lseal(tx);
  memset(rx,0,sizeof(rx));int rc=spi_transceive_cb(spi,&config,&ts,&rs,complete,NULL);
  if(rc){atomic_set(&fault,1);printk("SPI_LINK arm=%d\n",rc);return;}
  gpio_pin_set(gpio,5,1);
  static bool announced; if(!announced){printk("SPI_LINK armed=1 ready_pin=D2 no_rf=1\n");announced=true;}
  k_sem_take(&transferred,K_FOREVER);
  /* CS rising triggers completion. Leave READY low long enough for master to observe. */
  while(gpio_pin_get(gpio,21)==0)k_sleep(K_USEC(50));
  k_busy_wait(100);
  if(!lvalid(rx)||lget(rx+4)!=boot)continue;
  if(pending_len&&lget(rx+12)==output_seq)pending_len=0;
  if(lrequest_ok(rx,boot,accepted,atomic_get(&busy)||atomic_get(&fault)||queued()||pending_len)){
   memcpy(command,rx+20,rx[3]);command[rx[3]]=0;
   accepted=lget(rx+8);atomic_set(&busy,1);k_sem_give(&command_ready);
  }
 }
}
K_THREAD_DEFINE(link_spi_id,2560,link_worker,NULL,NULL,NULL,6,0,SYS_FOREVER_MS);
void ania_spi_start(void){fifo=shared_multi_heap_alloc(SMH_REG_ATTR_EXTERNAL,FIFO_SIZE);if(!fifo){atomic_set(&fault,1);return;}k_thread_start(link_spi_id);}
