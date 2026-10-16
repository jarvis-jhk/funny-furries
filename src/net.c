#ifndef _WIN32
#define _POSIX_C_SOURCE 200112L
#endif
#include "net.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
typedef int socklen_t;
#define CLOSE closesocket
#define WOULD_BLOCK (WSAGetLastError()==WSAEWOULDBLOCK||WSAGetLastError()==WSAEINPROGRESS)
#define BAD_FD ((intptr_t)INVALID_SOCKET)
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>
#include <sys/select.h>
#define CLOSE close
#define WOULD_BLOCK (errno==EAGAIN||errno==EWOULDBLOCK||errno==EINPROGRESS)
#define BAD_FD ((intptr_t)-1)
#endif
static void nonblocking(intptr_t fd) {
#ifdef _WIN32
    u_long on=1;ioctlsocket((SOCKET)fd,FIONBIO,&on);
#else
    fcntl((int)fd,F_SETFL,fcntl((int)fd,F_GETFL,0)|O_NONBLOCK);
#endif
}
bool ff_net_init(void) {
#ifdef _WIN32
    WSADATA data;return WSAStartup(MAKEWORD(2,2),&data)==0;
#else
    return true;
#endif
}
uint32_t ff_net_ms(void) {
#ifdef _WIN32
    return (uint32_t)GetTickCount64();
#else
    struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint32_t)((uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u);
#endif
}
static struct sockaddr_in socket_addr(FF_Addr a) {
    struct sockaddr_in s;memset(&s,0,sizeof(s));s.sin_family=AF_INET;
    s.sin_addr.s_addr=htonl(a.ip);s.sin_port=htons(a.port);return s;
}
static int env_number(const char *name,int high) {
    const char *v=getenv(name);if(!v) return 0;
    int n=atoi(v);return n<0?0:n>high?high:n;
}
bool ff_udp_open(FF_Udp *u,uint16_t port) {
    memset(u,0,sizeof(*u));
    u->fd=(intptr_t)socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(u->fd==BAD_FD) return false;
    int on=1;setsockopt((int)u->fd,SOL_SOCKET,SO_BROADCAST,(const char *)&on,sizeof(on));
    struct sockaddr_in s=socket_addr((FF_Addr){0,port});
    if(bind((int)u->fd,(struct sockaddr *)&s,sizeof(s))!=0) {
        s.sin_port=0;
        if(bind((int)u->fd,(struct sockaddr *)&s,sizeof(s))!=0) {CLOSE((int)u->fd);u->fd=BAD_FD;return false;}
    }
    socklen_t length=sizeof(s);getsockname((int)u->fd,(struct sockaddr *)&s,&length);u->port=ntohs(s.sin_port);
    nonblocking(u->fd);
    u->loss=env_number("FF_NET_LOSS",90);u->delay=env_number("FF_NET_DELAY",2000);u->jitter=env_number("FF_NET_JITTER",2000);
    u->rng=0x9e3779b9u^(uint32_t)u->port^ff_net_ms();
    return true;
}
void ff_udp_close(FF_Udp *u) {if(u->fd!=BAD_FD&&u->fd) CLOSE((int)u->fd);u->fd=BAD_FD;}
static uint32_t roll(FF_Udp *u,uint32_t n) {u->rng^=u->rng<<13;u->rng^=u->rng>>17;u->rng^=u->rng<<5;return n?u->rng%n:0;}
static void send_now(FF_Udp *u,FF_Addr to,const void *data,int length) {
    struct sockaddr_in s=socket_addr(to);
    sendto((int)u->fd,(const char *)data,length,0,(struct sockaddr *)&s,sizeof(s));
}
static void flush(FF_Udp *u) {
    uint32_t now=ff_net_ms();
    for(int i=0;i<u->queued;) {
        if((int32_t)(now-u->queue[i].due)>=0) {send_now(u,u->queue[i].to,u->queue[i].data,u->queue[i].length);u->queue[i]=u->queue[--u->queued];}
        else ++i;
    }
}
void ff_udp_send(FF_Udp *u,FF_Addr to,const void *data,int length) {
    if(u->fd==BAD_FD||length<=0||length>512) return;
    if(u->loss&&roll(u,100)<(uint32_t)u->loss) return;
    if((u->delay||u->jitter)&&u->queued<256) {
        FF_Delayed *d=&u->queue[u->queued++];
        d->due=ff_net_ms()+(uint32_t)u->delay+roll(u,(uint32_t)u->jitter+1);d->to=to;d->length=length;memcpy(d->data,data,(size_t)length);
        return;
    }
    send_now(u,to,data,length);
}
int ff_udp_recv(FF_Udp *u,FF_Addr *from,void *data,int capacity) {
    if(u->fd==BAD_FD) return -1;
    flush(u);
    struct sockaddr_in s;socklen_t length=sizeof(s);
    int n=(int)recvfrom((int)u->fd,(char *)data,capacity,0,(struct sockaddr *)&s,&length);
    if(n<0) return -1;
    from->ip=ntohl(s.sin_addr.s_addr);from->port=ntohs(s.sin_port);return n;
}
bool ff_resolve(const char *host,uint16_t port,FF_Addr *out) {
    struct addrinfo hints,*list=NULL;memset(&hints,0,sizeof(hints));
    hints.ai_family=AF_INET;hints.ai_socktype=SOCK_DGRAM;
    if(getaddrinfo(host,NULL,&hints,&list)!=0||!list) return false;
    out->ip=ntohl(((struct sockaddr_in *)list->ai_addr)->sin_addr.s_addr);out->port=port;
    freeaddrinfo(list);return true;
}
uint32_t ff_lan_ip(void) {
    /* Connecting a UDP socket sends nothing; it only picks the outgoing interface. */
    intptr_t fd=(intptr_t)socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(fd==BAD_FD) return 0;
    struct sockaddr_in s=socket_addr((FF_Addr){0x08080808u,53});uint32_t ip=0;
    if(connect((int)fd,(struct sockaddr *)&s,sizeof(s))==0) {
        socklen_t length=sizeof(s);if(getsockname((int)fd,(struct sockaddr *)&s,&length)==0) ip=ntohl(s.sin_addr.s_addr);
    }
    CLOSE((int)fd);return ip;
}
bool ff_addr_equal(FF_Addr a,FF_Addr b) {return a.ip==b.ip&&a.port==b.port;}
void ff_addr_text(FF_Addr a,char *out,unsigned capacity) {
    snprintf(out,capacity,"%u.%u.%u.%u:%u",a.ip>>24,(a.ip>>16)&255u,(a.ip>>8)&255u,a.ip&255u,a.port);
}
bool ff_addr_parse(const char *text,FF_Addr *out) {
    unsigned b[4],port=FF_NET_PORT;char tail;
    int n=sscanf(text,"%u.%u.%u.%u:%u%c",&b[0],&b[1],&b[2],&b[3],&port,&tail);
    if(n!=4&&n!=5) return false;
    for(int i=0;i<4;++i) if(b[i]>255) return false;
    if(!port||port>65535) return false;
    out->ip=b[0]<<24|b[1]<<16|b[2]<<8|b[3];out->port=(uint16_t)port;return true;
}
static void put16(uint8_t *p,unsigned v) {p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
static unsigned get16(const uint8_t *p) {return (unsigned)p[0]<<8|p[1];}
void ff_stun_request(FF_Udp *u,FF_Addr server,const uint8_t id[12]) {
    uint8_t m[20]={0};put16(m,1);put16(m+2,0);m[4]=0x21;m[5]=0x12;m[6]=0xA4;m[7]=0x42;memcpy(m+8,id,12);
    ff_udp_send(u,server,m,20);
}
bool ff_stun_response(const uint8_t *m,int length,const uint8_t id[12],FF_Addr *mapped) {
    if(length<20||get16(m)!=0x0101||m[4]!=0x21||m[5]!=0x12||m[6]!=0xA4||m[7]!=0x42||memcmp(m+8,id,12)) return false;
    int end=20+(int)get16(m+2);if(end>length) end=length;
    for(int at=20;at+4<=end;) {
        unsigned type=get16(m+at),size=get16(m+at+2);
        if(at+4+(int)size>end) break;
        const uint8_t *v=m+at+4;
        if((type==0x0020||type==0x0001)&&size>=8&&v[1]==1) {
            unsigned port=get16(v+2);uint32_t ip=(uint32_t)v[4]<<24|(uint32_t)v[5]<<16|(uint32_t)v[6]<<8|v[7];
            if(type==0x0020) {port^=0x2112;ip^=0x2112A442u;}
            mapped->ip=ip;mapped->port=(uint16_t)port;return true;
        }
        at+=4+(int)((size+3)&~3u);
    }
    return false;
}
static const char alphabet[]="0123456789ABCDEFGHJKMNPQRSTVWXYZ";
void ff_code_make(FF_Addr host,uint16_t token,char out[20]) {
    uint64_t v=(uint64_t)host.ip<<32|(uint64_t)host.port<<16|token;
    char raw[13];
    /* 64 bits in 13 base-32 letters; the last one holds four bits plus a check bit. */
    unsigned parity=0;for(int i=0;i<64;++i) parity^=(unsigned)(v>>i)&1u;
    raw[12]=alphabet[((v&15u)<<1)|parity];uint64_t rest=v>>4;
    for(int i=11;i>=0;--i) {raw[i]=alphabet[rest&31u];rest>>=5;}
    snprintf(out,20,"%.4s-%.4s-%.5s",raw,raw+4,raw+8);
}
static int letter(char c) {
    c=(char)toupper((unsigned char)c);
    if(c=='O') c='0';
    if(c=='I'||c=='L') c='1';
    const char *p=strchr(alphabet,c);return c&&p?(int)(p-alphabet):-1;
}
bool ff_code_read(const char *text,FF_Addr *host,uint16_t *token) {
    if(ff_addr_parse(text,host)) {*token=0;return true;}
    int value[13],n=0;
    for(const char *p=text;*p;++p) {
        if(*p=='-'||*p==' ') continue;
        int d=letter(*p);if(d<0||n==13) return false;value[n++]=d;
    }
    if(n!=13) return false;
    uint64_t v=0;for(int i=0;i<12;++i) v=v<<5|(uint64_t)value[i];
    v=v<<4|(uint64_t)(value[12]>>1);
    unsigned parity=0;for(int i=0;i<64;++i) parity^=(unsigned)(v>>i)&1u;
    if(parity!=((unsigned)value[12]&1u)) return false;
    host->ip=(uint32_t)(v>>32);host->port=(uint16_t)(v>>16);*token=(uint16_t)v;
    return host->ip&&host->port;
}
void ff_http_start(FF_Http *h,FF_Addr server,const char *request) {
    memset(h,0,sizeof(*h));h->state=-1;
    size_t length=strlen(request);if(length>=sizeof(h->out)) return;
    memcpy(h->out,request,length);h->out_length=(int)length;
    h->fd=(intptr_t)socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(h->fd==BAD_FD) return;
    nonblocking(h->fd);
    struct sockaddr_in s=socket_addr(server);
    if(connect((int)h->fd,(struct sockaddr *)&s,sizeof(s))!=0&&!WOULD_BLOCK) {CLOSE((int)h->fd);h->fd=BAD_FD;return;}
    h->state=0;h->deadline=ff_net_ms()+8000;
}
int ff_http_poll(FF_Http *h) {
    if(h->state<0) return -1;
    if(h->state==2) return 1;
    if((int32_t)(ff_net_ms()-h->deadline)>0) {ff_http_close(h);h->state=-1;return -1;}
    if(h->state==0) {
        fd_set writable;FD_ZERO(&writable);FD_SET((int)h->fd,&writable);
        struct timeval none={0,0};
        if(select((int)h->fd+1,NULL,&writable,NULL,&none)<=0) return 0;
        int error=0;socklen_t size=sizeof(error);
        getsockopt((int)h->fd,SOL_SOCKET,SO_ERROR,(char *)&error,&size);
        if(error) {ff_http_close(h);h->state=-1;return -1;}
        h->state=1;
    }
    while(h->sent<h->out_length) {
        int n=(int)send((int)h->fd,h->out+h->sent,h->out_length-h->sent,0);
        if(n<0) {if(WOULD_BLOCK) return 0;ff_http_close(h);h->state=-1;return -1;}
        h->sent+=n;
    }
    for(;;) {
        if(h->in_length>=(int)sizeof(h->in)-1) break;
        int n=(int)recv((int)h->fd,h->in+h->in_length,(int)sizeof(h->in)-1-h->in_length,0);
        if(n<0) {if(WOULD_BLOCK) return 0;ff_http_close(h);h->state=-1;return -1;}
        if(n==0) break;
        h->in_length+=n;
    }
    h->in[h->in_length]=0;ff_http_close(h);h->state=2;return 1;
}
void ff_http_close(FF_Http *h) {if(h->fd!=BAD_FD&&h->fd) CLOSE((int)h->fd);h->fd=BAD_FD;}
