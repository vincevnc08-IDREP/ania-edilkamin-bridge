/* SPDX-License-Identifier: GPL-3.0-or-later
 * Nano 33 IoT: WiFiNINA TCP bridge, external SPI master, no RF replay.
 * NINA uses SPI1; SPI below is the external D11/D12/D13 bus.
 */
#include <SPI.h>
#include <WiFiNINA.h>
#include "link_protocol.h"
#include "secrets.h"
const int CS_PIN=10, READY_PIN=2;
WiFiServer server(18765);
WiFiClient client;
uint32_t bootId=0, ackOutput=0, accepted=0, flags=LINK_BUSY;
uint32_t pendingId=0, pendingSince=0, lastGood=0, lastWifiTry=0, connectedSince=0;
uint32_t lastFlush=0, lastWifiCheck=0, spiGood=0, spiBad=0, spiHandshakeErrors=0;
int wifiStatus=WL_IDLE_STATUS;
char pendingCommand[41], line[112];size_t lineLen=0;
uint8_t netOut[1440];size_t netUsed=0;
bool authenticated=false, linkSynced=false, serverStarted=false;

void disconnectClient() {
 if(client)client.stop();authenticated=false;lineLen=0;pendingId=0;netUsed=0;
}
bool tokenMatches(const char *s) {
 const char *t=ANIA_LINK_TOKEN;size_t n=strlen(t);if(strlen(s)!=n)return false;
 uint8_t d=0;for(size_t i=0;i<n;i++)d|=(uint8_t)(s[i]^t[i]);return d==0;
}
void flushNetwork() {
 if(!netUsed)return;
 if(!authenticated||!client.connected()){netUsed=0;return;}
 size_t sent=client.write(netOut,netUsed);
 if(sent!=netUsed){disconnectClient();return;}
 netUsed=0;lastFlush=millis();
}
void spiTick() {
 static uint32_t lastTransaction=0;
 if((uint32_t)(micros()-lastTransaction)<1000 || !digitalRead(READY_PIN))return;
 lastTransaction=micros();
 uint8_t tx[64]={0},rx[64];lput(tx+4,bootId);lput(tx+12,ackOutput);
 if(pendingId){tx[3]=strlen(pendingCommand);lput(tx+8,pendingId);memcpy(tx+20,pendingCommand,tx[3]);}
 lseal(tx);SPI.beginTransaction(SPISettings(2000000,MSBFIRST,SPI_MODE0));digitalWrite(CS_PIN,LOW);delayMicroseconds(3);
 for(unsigned i=0;i<64;i++)rx[i]=SPI.transfer(tx[i]);
 /* CS rising completes the ESP32 target transaction and triggers READY low. */
 delayMicroseconds(3);digitalWrite(CS_PIN,HIGH);SPI.endTransaction();
 uint32_t start=micros();while(digitalRead(READY_PIN)&&(uint32_t)(micros()-start)<10000){}
 bool handshake=!digitalRead(READY_PIN);
 if(!handshake){spiHandshakeErrors++;return;}
 if(!lvalid(rx)){spiBad++;return;}
 spiGood++;
 lastGood=millis();uint32_t b=lget(rx+4);
 if(b!=bootId){disconnectClient();bootId=b;linkSynced=false;ackOutput=lget(rx+8);}
 accepted=lget(rx+12);flags=lget(rx+16);
 if(flags&LINK_FAULT){disconnectClient();linkSynced=false;return;}
 uint32_t seq=lget(rx+8);
 if(rx[3]&&seq!=ackOutput){
  if(authenticated&&seq!=ackOutput+1){disconnectClient();}
  if(authenticated){
   if(netUsed+rx[3]>sizeof(netOut))flushNetwork();
   if(authenticated){memcpy(netOut+netUsed,rx+20,rx[3]);netUsed+=rx[3];}
  }
  ackOutput=seq;
 }
 if(pendingId&&accepted==pendingId)pendingId=0;
 if(!(flags&LINK_BUSY))linkSynced=true;
}
void setup() {
 pinMode(CS_PIN,OUTPUT);digitalWrite(CS_PIN,HIGH);pinMode(READY_PIN,INPUT_PULLDOWN);
 SPI.begin();Serial.begin(115200);WiFi.setTimeout(3000);
 // No wait for USB. Boot is passive: no command to the stove.
 lastWifiTry=millis()-15000u;
}
void loop() {
 if(Serial.available() && Serial.read()=='?') {
  Serial.print("ANIA_IOT version=13 wifi_status=");Serial.print(wifiStatus);
  Serial.print(" ip=");Serial.print(WiFi.localIP());
  Serial.print(" ready_pin=");Serial.print(digitalRead(READY_PIN));
  Serial.print(" spi_good=");Serial.print(spiGood);Serial.print(" spi_bad=");Serial.print(spiBad);
  Serial.print(" spi_handshake_errors=");Serial.print(spiHandshakeErrors);
  Serial.print(" boot_id=");Serial.print(bootId);Serial.print(" flags=");Serial.print(flags);
  Serial.print(" synced=");Serial.print(linkSynced);Serial.print(" pending=");Serial.println(pendingId);
 }
 if(client&&!client.connected())disconnectClient();
 if(pendingId&&(uint32_t)(millis()-pendingSince)>2000)disconnectClient();
 for(unsigned i=0;i<32;i++){spiTick();if(netUsed>=1400)break;delayMicroseconds(30);}
 if((uint32_t)(millis()-lastGood)>2000){disconnectClient();linkSynced=false;}
 if(netUsed&&(netUsed>=1400||(uint32_t)(millis()-lastFlush)>=5))flushNetwork();
 if((uint32_t)(millis()-lastWifiCheck)>=1000){lastWifiCheck=millis();wifiStatus=WiFi.status();}
 if(wifiStatus!=WL_CONNECTED){
  disconnectClient();serverStarted=false;
  if((uint32_t)(millis()-lastWifiTry)>=15000){lastWifiTry=millis();
   wifiStatus=WiFi.begin(ANIA_WIFI_SSID,ANIA_WIFI_PASSWORD);
  }
  return;
 }
 if(!serverStarted){server.begin();serverStarted=true;Serial.print("ANIA dual IP: ");Serial.println(WiFi.localIP());}
 if(!client){
  WiFiClient incoming=server.available();
  if(incoming){
   if(!linkSynced||(flags&LINK_BUSY)||(flags&LINK_FAULT)){incoming.stop();return;}
   client=incoming;connectedSince=millis();lineLen=0;authenticated=false;
  }
 }
 if(!client)return;
 if(!authenticated&&(uint32_t)(millis()-connectedSince)>5000){disconnectClient();return;}
 while(client.available()){
  int v=client.read();if(v<0)break;char c=(char)v;
  if(c=='\r'||c=='\n'){
   if(!lineLen)continue;line[lineLen]=0;lineLen=0;
   if(!authenticated){
    if(strncmp(line,"AUTH ",5)||!tokenMatches(line+5)){disconnectClient();return;}
    authenticated=true;client.print("ANIA_DUAL 1\n");
   }else{
    if(pendingId||!lcommand(line)||strlen(line)>40){disconnectClient();return;}
    strcpy(pendingCommand,line);pendingId=accepted+1;pendingSince=millis();
    // Never accept a second command until acknowledged and output drained.
    flags|=LINK_BUSY;
   }
  }else{
   if(c<32||c>126||lineLen>=sizeof(line)-1){disconnectClient();return;}line[lineLen++]=c;
  }
 }
}
