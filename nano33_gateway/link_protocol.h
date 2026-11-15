/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef ANIA_LINK_PROTOCOL_H
#define ANIA_LINK_PROTOCOL_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define LINK_SIZE 64
#define LINK_DATA 40
#define LINK_BUSY 1u
#define LINK_FAULT 2u
static inline uint32_t lget(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static inline void lput(uint8_t *p,uint32_t v) {for(int i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static inline uint32_t lcrc(const uint8_t *p,size_t n) {uint32_t c=~0u;while(n--){c^=*p++;for(int j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static inline void lseal(uint8_t *p) {p[0]='A';p[1]='N';p[2]=1;lput(p+60,lcrc(p,60));}
static inline int lvalid(const uint8_t *p) {return p[0]=='A'&&p[1]=='N'&&p[2]==1&&p[3]<=LINK_DATA&&lget(p+60)==lcrc(p,60);}
/* Fixed command allowlist; no arbitrary shell, duration or absolute on/off. */
static inline int lcommand(const char *s) {
 if(!strcmp(s,"tx long_poll 10"))return 1;
 const char *gains[]={"rx gain -1","rx gain 20","rx gain 30","rx gain 40","rx gain 50","rx gain 60","rx gain 70","rx gain 80"};
 for(unsigned i=0;i<8;i++)if(!strcmp(s,gains[i]))return 1;
 if(!strcmp(s,"tx menu_hold3s 10")||!strcmp(s,"tx menu_exit_once 10"))return 1;
 if(!strcmp(s,"tx power_hold3s 10"))return 1;
 if(!strcmp(s,"rx capture 500")||!strcmp(s,"rx listen 500"))return 1;
 if(!strcmp(s,"rx status")||!strcmp(s,"tx check"))return 1;
 for(unsigned g=0;g<=12;g++) {
  char num[3];unsigned n=0;if(g>=10)num[n++]='1';num[n++]=(char)('0'+g%10);num[n]=0;
  const char *prefix[]={"tx plus_once ","tx minus_once ","tx manual_once ","tx automatic_once ","tx poll ","tx fast_poll "};
  for(unsigned i=0;i<6;i++){char c[40];strcpy(c,prefix[i]);strcat(c,num);
   if(i<4){if(!strcmp(c,s))return 1;}else{strcat(c," 100 ");size_t z=strlen(c);strcpy(c+z,"8");if(!strcmp(c,s))return 1;strcpy(c+z,"20");if(!strcmp(c,s))return 1;}
  }
 }
 return 0;
}
/* Accept a complete new request only after all prior output was acknowledged. */
static inline int lrequest_ok(const uint8_t *p,uint32_t boot,uint32_t accepted,int blocked) {
 if(blocked||!lvalid(p)||lget(p+4)!=boot||!p[3]||lget(p+8)!=accepted+1)return 0;
 char cmd[LINK_DATA+1];memcpy(cmd,p+20,p[3]);cmd[p[3]]=0;
 return strlen(cmd)==p[3]&&lcommand(cmd);
}
#endif
