#include "net.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static void codes(void) {
    FF_Addr a={0x5DB8D822u,27590},b;uint16_t token;char code[20];
    ff_code_make(a,0xBEEF,code);
    CHECK(strlen(code)==15&&code[4]=='-'&&code[9]=='-');
    CHECK(ff_code_read(code,&b,&token));CHECK(ff_addr_equal(a,b));CHECK(token==0xBEEF);
    /* Typed in lower case, without dashes, with O for zero and I/L for one. */
    char typed[20];int n=0;
    for(const char *p=code;*p;++p) if(*p!='-') typed[n++]=(char)(*p=='0'?'o':*p=='1'?'l':*p>='A'&&*p<='Z'?*p+32:*p);
    typed[n]=0;CHECK(ff_code_read(typed,&b,&token));CHECK(ff_addr_equal(a,b));CHECK(token==0xBEEF);
    /* One wrong letter is caught by the check bit or decodes to another host; never silently the same. */
    unsigned caught=0;
    for(int i=0;i<15;++i) {
        if(code[i]=='-') continue;
        char wrong[20];memcpy(wrong,code,20);wrong[i]=wrong[i]=='Z'?'Y':'Z';
        if(!ff_code_read(wrong,&b,&token)) ++caught;
        else CHECK(!ff_addr_equal(a,b)||token!=0xBEEF);
    }
    CHECK(caught>0);
    CHECK(!ff_code_read("ABC",&b,&token));CHECK(!ff_code_read("AAAA-AAAA-AAAAU",&b,&token));
    CHECK(ff_code_read("192.168.1.20:27590",&b,&token));CHECK(b.ip==0xC0A80114u&&b.port==27590&&token==0);
    CHECK(ff_code_read("10.0.0.7",&b,&token));CHECK(b.port==FF_NET_PORT);
    CHECK(!ff_code_read("300.1.1.1:5",&b,&token));CHECK(!ff_code_read("1.2.3.4:0",&b,&token));
    char text[32];ff_addr_text(a,text,sizeof(text));CHECK(!strcmp(text,"93.184.216.34:27590"));
}
static void stun(void) {
    uint8_t id[12]={1,2,3,4,5,6,7,8,9,10,11,12};
    /* Binding success with an XOR-MAPPED-ADDRESS for 93.184.216.34:27590 (RFC 5389 section 15.2). */
    uint8_t m[32]={0x01,0x01,0,12,0x21,0x12,0xA4,0x42};memcpy(m+8,id,12);
    m[20]=0;m[21]=0x20;m[22]=0;m[23]=8;m[24]=0;m[25]=1;
    unsigned port=27590^0x2112u;m[26]=(uint8_t)(port>>8);m[27]=(uint8_t)port;
    uint32_t ip=0x5DB8D822u^0x2112A442u;m[28]=(uint8_t)(ip>>24);m[29]=(uint8_t)(ip>>16);m[30]=(uint8_t)(ip>>8);m[31]=(uint8_t)ip;
    FF_Addr a;CHECK(ff_stun_response(m,32,id,&a));CHECK(a.ip==0x5DB8D822u&&a.port==27590);
    id[0]=9;CHECK(!ff_stun_response(m,32,id,&a));id[0]=1;
    m[3]=200;CHECK(ff_stun_response(m,32,id,&a));   /* a lying length is clipped to what arrived */
    CHECK(!ff_stun_response(m,19,id,&a));
}
int main(void) {codes();stun();printf("net checks=%u\n",checks);return 0;}
