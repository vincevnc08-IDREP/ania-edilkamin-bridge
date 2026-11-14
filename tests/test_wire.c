#include <assert.h>
#include <stdio.h>
#include "../nano33_gateway/link_protocol.h"
int main(void){
 uint8_t guard[8]={1,2,3,4,5,6,7,8};lput(guard+2,0x12345678);assert(guard[0]==1&&guard[1]==2&&guard[6]==7&&guard[7]==8);assert(lget(guard+2)==0x12345678);
 assert(lcrc((const uint8_t*)"123456789",9)==0xcbf43926);
 uint8_t p[64]={0};p[3]=strlen("tx plus_once 10");memcpy(p+20,"tx plus_once 10",p[3]);lput(p+4,123);lput(p+8,8);lseal(p);
 assert(lrequest_ok(p,123,7,0));
 assert(!lrequest_ok(p,123,8,0)); /* Lost ACK -> duplicated request never executes. */
 assert(!lrequest_ok(p,124,7,0)); /* Old boot session never executes. */
 assert(!lrequest_ok(p,123,6,0)); /* Out-of-order request. */
 assert(!lrequest_ok(p,123,7,1)); /* Busy/fault/pending output. */
 for(int i=0;i<512;i++){p[i/8]^=1u<<(i%8);assert(!lvalid(p));p[i/8]^=1u<<(i%8);}
 p[22]=0;lseal(p);assert(!lrequest_ok(p,123,7,0));
 const char *bad[]={"tx off","reboot","tx plus_once 13","tx plus_once -1","tx poll 10 100 3000","tx poll 10 100 8;tx plus_once 10","tx check\n","tx plus_once 10 extra",""};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++)assert(!lcommand(bad[i]));
 assert(lcommand("rx status"));assert(lcommand("tx check"));assert(lcommand("tx poll 12 100 20"));assert(lcommand("tx minus_once 0"));
 assert(lcommand("tx power_hold3s 10"));assert(!lcommand("tx power_hold3s 10 3000"));assert(!lcommand("tx power_hold3s 11"));
 puts("wire: CRC reference, 512 bit flips, duplicate/stale/busy requests, command grammar passed");
}
