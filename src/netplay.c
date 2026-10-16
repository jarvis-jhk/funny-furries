#include "netplay.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
enum { HELLO=1, WELCOME, REJECT, LOBBY, START, INPUT, QUIT, PUNCH };
enum { FULL=1, OTHER_ARENA, STARTED, OLD_VERSION };
#define VERSION 1
#define HEADER 6
#define RELAY_HOST "ntfy.sh"
static void put32(uint8_t *p,uint32_t v) {p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static uint32_t get32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t fnv(uint32_t h,const void *data,size_t size) {
    const uint8_t *p=data;while(size--) {h^=*p++;h*=16777619u;}
    return h;
}
uint32_t ff_arena_fingerprint(const FF_Arena *a) {
    /* Everything the simulation reads; two machines must agree on all of it. */
    uint32_t h=2166136261u;
    h=fnv(h,a->tiles,sizeof(a->tiles));h=fnv(h,a->mask,sizeof(a->mask));
    h=fnv(h,a->spawns,sizeof(a->spawns));h=fnv(h,&a->spawn_count,sizeof(a->spawn_count));
    h=fnv(h,a->muzzles,sizeof(a->muzzles));h=fnv(h,a->bonuses,sizeof(a->bonuses));h=fnv(h,&a->bonus_count,sizeof(a->bonus_count));
    h=fnv(h,a->blast_boxes,sizeof(a->blast_boxes));h=fnv(h,a->devices,sizeof(a->devices));
    h=fnv(h,&a->device_count,sizeof(a->device_count));h=fnv(h,a->paths,sizeof(a->paths));
    uint8_t imported=a->imported;return fnv(h,&imported,1);
}
static void header(uint8_t *p,int type,uint16_t token) {p[0]='F';p[1]='N';p[2]=VERSION;p[3]=(uint8_t)type;p[4]=(uint8_t)token;p[5]=(uint8_t)(token>>8);}
static void send_type(FF_Netplay *np,FF_Addr to,int type,const uint8_t *body,int size) {
    uint8_t p[512];header(p,type,np->token);
    if(size) memcpy(p+HEADER,body,(size_t)size);
    ff_udp_send(&np->udp,to,p,HEADER+size);
}
static int seat_count(unsigned seats) {int n=0;for(int i=0;i<FF_PLAYERS;++i) n+=(seats>>i)&1u;return n;}
static uint32_t random_seed(void) {
    static uint32_t salt=0x6a09e667u;
    salt=(salt*1664525u+1013904223u)^ff_net_ms();
    uint32_t local=ff_lan_ip();return fnv(2166136261u,&salt,4)^fnv(2166136261u,&local,4);
}
static void make_topic(FF_Netplay *np,FF_Addr host,uint16_t token) {
    uint8_t raw[8]={(uint8_t)(host.ip>>24),(uint8_t)(host.ip>>16),(uint8_t)(host.ip>>8),(uint8_t)host.ip,(uint8_t)(host.port>>8),(uint8_t)host.port,(uint8_t)(token>>8),(uint8_t)token};
    uint32_t a=fnv(0x811c9dc5u,raw,8),b=fnv(a^0x5bd1e995u,"funny-furries-join",18);
    snprintf(np->topic,sizeof(np->topic),"ff-join-%08x%08x",a,b);
}
static bool common_open(FF_Netplay *np,const FF_Arena *a,int local_count,uint16_t port,bool internet) {
    memset(np,0,sizeof(*np));
    for(int i=0;i<FF_PLAYERS;++i) np->owner[i]=-1;
    if(!ff_net_init()||!ff_udp_open(&np->udp,port)) {snprintf(np->status,sizeof(np->status),"NO NETWORK");return false;}
    np->local_count=local_count<1?1:local_count>3?3:local_count;np->arena=a;np->arena_hash=ff_arena_fingerprint(a);np->nonce=random_seed();
    np->lan_addr=(FF_Addr){ff_lan_ip(),np->udp.port};ff_addr_text(np->lan_addr,np->lan_text,sizeof(np->lan_text));
    np->phase=FF_NP_LOBBY;
    if(internet) {
        int servers=0;
        if(ff_resolve("stun.l.google.com",19302,&np->stun[servers])) ++servers;
        if(ff_resolve("stun.cloudflare.com",3478,&np->stun[servers])) ++servers;
        if(servers) {
            uint32_t r=random_seed();for(int i=0;i<12;++i) {np->stun_id[i]=(uint8_t)r;r=r*1103515245u+12345u;}
            np->stun_until=ff_net_ms()+5000;
        }
        np->relay_ok=ff_resolve(RELAY_HOST,80,&np->relay);
    }
    return true;
}
bool ff_np_host(FF_Netplay *np,const FF_Arena *a,int local_count,uint16_t port,bool internet) {
    if(!common_open(np,a,local_count,port,internet)) return false;
    np->host=true;np->me=0;np->token=(uint16_t)(random_seed()|1u);
    np->peers[0].used=true;np->peers[0].local_count=np->local_count;
    for(int i=0;i<np->local_count;++i) {np->owner[i]=0;np->seats|=1u<<i;}
    np->peers[0].seats=np->local_seats=np->seats;
    ff_code_make(np->lan_addr,np->token,np->code);
    snprintf(np->status,sizeof(np->status),internet?"FINDING INTERNET ADDRESS":"LOCAL NETWORK ONLY");
    return true;
}
bool ff_np_join(FF_Netplay *np,const FF_Arena *a,const char *code,int local_count,bool internet) {
    FF_Addr host;uint16_t token;
    if(!ff_code_read(code,&host,&token)) {memset(np,0,sizeof(*np));snprintf(np->status,sizeof(np->status),"THAT CODE IS NOT VALID");return false;}
    if(!common_open(np,a,local_count,0,internet&&token)) return false;
    np->host=false;np->token=token;np->direct=host;np->direct_join=!token;
    np->peers[0].used=true;np->peers[0].addr=host;np->peers[0].heard=ff_net_ms();
    snprintf(np->code,sizeof(np->code),"%s",code);
    if(token) make_topic(np,host,token);
    np->me=-1;snprintf(np->status,sizeof(np->status),"CONNECTING");
    return true;
}
int ff_np_seat_of_local(const FF_Netplay *np,int local) {
    for(int s=0,n=0;s<FF_PLAYERS;++s) if((np->local_seats>>s)&1u) {if(n==local) return s;++n;}
    return -1;
}
static void end(FF_Netplay *np,const char *why) {
    if(np->phase==FF_NP_ENDED) return;
    np->phase=FF_NP_ENDED;snprintf(np->ended,sizeof(np->ended),"%s",why);snprintf(np->status,sizeof(np->status),"%s",why);
}
static void lobby_packet(FF_Netplay *np,FF_Addr to) {
    uint8_t b[8]={(uint8_t)np->seats,(uint8_t)np->mode};
    for(int s=0;s<FF_PLAYERS;++s) b[2+s]=(uint8_t)(np->owner[s]+1);
    send_type(np,to,LOBBY,b,6);
}
static void start_packet(FF_Netplay *np,FF_Addr to) {
    uint8_t b[16];put32(b,np->seed);b[4]=(uint8_t)np->seats;b[5]=(uint8_t)np->mode;b[6]=(uint8_t)np->rb.delay;
    for(int s=0;s<FF_PLAYERS;++s) b[7+s]=(uint8_t)(np->owner[s]+1);
    send_type(np,to,START,b,11);
}
static int peer_at(const FF_Netplay *np,FF_Addr a) {
    for(int i=1;i<FF_NP_PEERS;++i) if(np->peers[i].used&&ff_addr_equal(np->peers[i].addr,a)) return i;
    return -1;
}
static void drop_peer(FF_Netplay *np,int p) {
    for(int s=0;s<FF_PLAYERS;++s) if(np->owner[s]==p) {np->owner[s]=-1;np->seats&=~(1u<<s);}
    memset(&np->peers[p],0,sizeof(np->peers[p]));
}
static void begin(FF_Netplay *np) {
    ff_game_setup(&np->start,np->arena,np->seed,np->seats,np->mode);
    np->local_seats=0;for(int s=0;s<FF_PLAYERS;++s) if(np->owner[s]==np->me) np->local_seats|=1u<<s;
    ff_rb_init(&np->rb,&np->start,np->seats,np->local_seats,np->rb.delay?np->rb.delay:FF_NP_DELAY);
    np->phase=FF_NP_PLAYING;np->stalled=0;
    uint32_t now=ff_net_ms();for(int i=0;i<FF_NP_PEERS;++i) if(np->peers[i].used) {np->peers[i].heard=now;memset(np->peers[i].ack,0,sizeof(np->peers[i].ack));}
    snprintf(np->status,sizeof(np->status),"PLAYING");
}
bool ff_np_can_start(const FF_Netplay *np,int mode) {
    if(!np->host||np->phase!=FF_NP_LOBBY) return false;
    bool guest=false;for(int i=1;i<FF_NP_PEERS;++i) guest|=np->peers[i].used;
    int n=seat_count(np->seats);return guest&&(mode==FF_TEAMS?n==4:n>=2);
}
void ff_np_start(FF_Netplay *np,int mode,uint32_t seed) {
    if(!ff_np_can_start(np,mode)) return;
    np->mode=mode;np->seed=seed?seed:random_seed()|1u;np->rb.delay=FF_NP_DELAY;
    begin(np);
    for(int i=1;i<FF_NP_PEERS;++i) if(np->peers[i].used) start_packet(np,np->peers[i].addr);
}
static void handle_input(FF_Netplay *np,int p,const uint8_t *b,int size) {
    if(size<4+1+16+8+1||np->phase!=FF_NP_PLAYING) return;
    FF_Peer *peer=&np->peers[p];peer->heard=ff_net_ms();peer->started=true;
    uint32_t frame=get32(b);if(frame>peer->frame) peer->frame=frame;
    peer->advantage=(int8_t)b[4];
    for(int s=0;s<FF_PLAYERS;++s) {uint32_t ack=get32(b+5+4*s);if(ack>peer->ack[s]) peer->ack[s]=ack;}
    ff_rb_remote_check(&np->rb,get32(b+21),get32(b+25));
    int ranges=b[29],at=30;
    for(int r=0;r<ranges;++r) {
        if(at+6>size) return;
        int seat=b[at];uint32_t first=get32(b+at+1);int count=b[at+5];at+=6;
        if(at+count>size||seat>=FF_PLAYERS) return;
        /* The host takes from a guest only that guest's seats; nobody overrides its own. */
        bool allowed=np->host?np->owner[seat]==p:np->owner[seat]!=np->me;
        if(allowed) for(int k=0;k<count;++k) ff_rb_input(&np->rb,seat,first+(uint32_t)k,b[at+k]);
        at+=count;
    }
}
static void send_input(FF_Netplay *np,int p) {
    FF_Peer *peer=&np->peers[p];uint8_t b[400];
    put32(b,np->rb.frame);
    int advantage=(int)np->rb.frame-(int)peer->frame;b[4]=(uint8_t)(int8_t)(advantage<-120?-120:advantage>120?120:advantage);
    for(int s=0;s<FF_PLAYERS;++s) put32(b+5+4*s,np->rb.confirmed[s]);
    uint32_t frame=0,hash=0;ff_rb_last_check(&np->rb,&frame,&hash);put32(b+21,frame);put32(b+25,hash);
    int ranges=0,at=30;
    for(int s=0;s<FF_PLAYERS;++s) {
        if(!((np->seats>>s)&1u)) continue;
        bool send=np->host?np->owner[s]!=p:np->owner[s]==np->me;
        if(!send) continue;
        uint32_t end=np->rb.confirmed[s],first=peer->ack[s];
        if(first>=end) continue;
        if(end-first>64) end=first+64;
        b[at]=(uint8_t)s;put32(b+at+1,first);b[at+5]=(uint8_t)(end-first);at+=6;
        for(uint32_t f=first;f<end;++f) b[at++]=np->rb.input[f%FF_RB_RING][s];
        ++ranges;
    }
    b[29]=(uint8_t)ranges;send_type(np,peer->addr,INPUT,b,at);
}
static void add_punch(FF_Netplay *np,FF_Addr a) {
    if(ff_addr_equal(a,np->public_addr)||ff_addr_equal(a,np->lan_addr)) return;
    for(int i=0;i<np->punch_count;++i) if(ff_addr_equal(np->punch[i],a)) return;
    if(np->punch_count==8) return;
    np->punch[np->punch_count]=a;np->punch_until[np->punch_count++]=ff_net_ms()+30000;
}
static void relay_poll(FF_Netplay *np,uint32_t now) {
    if(!np->relay_ok||!np->topic[0]) return;
    if(np->http_busy) {
        int r=ff_http_poll(&np->http);if(!r) return;
        np->http_busy=false;
        if(r>0&&np->host) {
            /* ntfy answers one JSON object per line; take every "message" that is an address. */
            for(const char *p=strstr(np->http.in,"\"message\":\"");p;p=strstr(p+1,"\"message\":\"")) {
                char text[40];int n=0;const char *q=p+11;
                while(*q&&*q!='"'&&n<39) text[n++]=*q++;
                text[n]=0;FF_Addr a;if(ff_addr_parse(text,&a)) add_punch(np,a);
            }
        }
        if(r>0&&!np->host) np->posted=true;
    }
    if((int32_t)(now-np->next_poll)<0) return;
    char request[512];
    if(np->host) {
        if(np->phase!=FF_NP_LOBBY) return;
        snprintf(request,sizeof(request),"GET /%s/json?poll=1&since=3m HTTP/1.0\r\nHost: %s\r\nUser-Agent: funny-furries\r\n\r\n",np->topic,RELAY_HOST);
        /* ntfy.sh refills an anonymous client about once per five seconds. */
        np->next_poll=now+5000;
    } else {
        if(!np->have_public||np->me>=0) return;
        char body[32];ff_addr_text(np->public_addr,body,sizeof(body));
        snprintf(request,sizeof(request),"POST /%s HTTP/1.0\r\nHost: %s\r\nUser-Agent: funny-furries\r\nContent-Length: %u\r\n\r\n%s",np->topic,RELAY_HOST,(unsigned)strlen(body),body);
        np->next_poll=now+(np->posted?20000:6000);
    }
    ff_http_start(&np->http,np->relay,request);np->http_busy=np->http.state>=0;
}
static void handle(FF_Netplay *np,FF_Addr from,const uint8_t *m,int size) {
    FF_Addr mapped;
    if(np->stun_until&&ff_stun_response(m,size,np->stun_id,&mapped)) {
        np->stun_until=0;np->public_addr=mapped;np->have_public=true;
        if(np->host) {
            ff_code_make(mapped,np->token,np->code);make_topic(np,mapped,np->token);
            snprintf(np->status,sizeof(np->status),"WAITING FOR PLAYERS");
        }
        return;
    }
    if(size<HEADER||m[0]!='F'||m[1]!='N') return;
    int type=m[3];uint16_t token=(uint16_t)(m[4]|m[5]<<8);const uint8_t *b=m+HEADER;size-=HEADER;
    if(m[2]!=VERSION) {
        if(np->host&&type==HELLO) {uint8_t why=OLD_VERSION;send_type(np,from,REJECT,&why,1);}
        if(!np->host&&type==REJECT) end(np,"DIFFERENT GAME VERSION");
        return;
    }
    uint32_t now=ff_net_ms();
    if(np->host) {
        if(token!=np->token&&!(type==HELLO&&token==0)) return;
        int p=peer_at(np,from);
        if(type==HELLO&&size>=9) {
            uint32_t nonce=get32(b+5);
            /* The same guest heard twice (LAN broadcast and public address): answer one path only. */
            for(int i=1;i<FF_NP_PEERS;++i) if(np->peers[i].used&&np->peers[i].nonce==nonce&&i!=p) return;
            if(p<0) {
                uint8_t why=0;int want=b[0]<1?1:b[0]>3?3:b[0];
                if(get32(b+1)!=np->arena_hash) why=OTHER_ARENA;
                else if(np->phase!=FF_NP_LOBBY) why=STARTED;
                else if(seat_count(np->seats)+want>FF_PLAYERS) why=FULL;
                for(int i=1;i<FF_NP_PEERS&&!why&&p<0;++i) if(!np->peers[i].used) p=i;
                if(p<0) {if(!why) why=FULL;send_type(np,from,REJECT,&why,1);return;}
                FF_Peer *peer=&np->peers[p];memset(peer,0,sizeof(*peer));peer->used=true;peer->addr=from;peer->local_count=want;peer->nonce=nonce;
                for(int s=0;s<FF_PLAYERS&&want;++s) if(np->owner[s]<0) {np->owner[s]=p;np->seats|=1u<<s;peer->seats|=1u<<s;--want;}
            }
            np->peers[p].heard=now;
            uint8_t w[2]={(uint8_t)p,(uint8_t)np->peers[p].seats};send_type(np,from,WELCOME,w,2);
            lobby_packet(np,from);
            if(np->phase==FF_NP_PLAYING) start_packet(np,from);
            return;
        }
        if(p<0) return;
        np->peers[p].heard=now;
        if(type==INPUT) handle_input(np,p,b,size);
        if(type==QUIT) {if(np->phase==FF_NP_PLAYING) end(np,"A PLAYER LEFT");else drop_peer(np,p);}
        return;
    }
    if(token!=np->token&&!(np->direct_join&&(type==WELCOME||type==REJECT))) return;
    if(type==WELCOME&&size>=2&&np->me<0) {
        /* A LAN broadcast is answered from the host's local address; talk to that. */
        if(np->direct_join) np->token=token;
        np->peers[0].addr=from;np->me=b[0];np->local_seats=b[1];
        snprintf(np->status,sizeof(np->status),"WAITING FOR THE HOST TO START");
    }
    if(!ff_addr_equal(from,np->peers[0].addr)) return;
    np->peers[0].heard=now;
    if(type==REJECT&&size>=1) end(np,b[0]==OTHER_ARENA?"THE HOST HAS A DIFFERENT ARENA":b[0]==STARTED?"THAT MATCH HAS ALREADY STARTED":"THAT MATCH IS FULL");
    if(type==LOBBY&&size>=6&&np->phase==FF_NP_LOBBY) {
        np->seats=b[0];np->mode=b[1];for(int s=0;s<FF_PLAYERS;++s) np->owner[s]=(int)b[2+s]-1;
    }
    if(type==START&&size>=11&&np->phase==FF_NP_LOBBY&&np->me>=0) {
        np->seed=get32(b);np->seats=b[4];np->mode=b[5];np->rb.delay=b[6];
        for(int s=0;s<FF_PLAYERS;++s) np->owner[s]=(int)b[7+s]-1;
        begin(np);
    }
    if(type==INPUT) handle_input(np,0,b,size);
    if(type==QUIT) end(np,"THE HOST LEFT");
}
void ff_np_poll(FF_Netplay *np) {
    if(np->phase==FF_NP_OFF) return;
    uint8_t m[600];FF_Addr from;int n;
    while((n=ff_udp_recv(&np->udp,&from,m,sizeof(m)))>=0) if(np->phase!=FF_NP_ENDED) handle(np,from,m,n);
    uint32_t now=ff_net_ms();
    if(np->phase==FF_NP_ENDED) return;
    if(np->stun_until) {
        if((int32_t)(now-np->stun_until)>0) {
            np->stun_until=0;
            if(np->host) snprintf(np->status,sizeof(np->status),"NO INTERNET ADDRESS - LOCAL NETWORK ONLY");
        } else if((int32_t)(now-np->next_hello)>=0) for(int i=0;i<2;++i) if(np->stun[i].ip) ff_stun_request(&np->udp,np->stun[i],np->stun_id);
    }
    relay_poll(np,now);
    bool tick=(int32_t)(now-np->next_hello)>=0;
    if(tick) np->next_hello=now+250;
    if(np->host) {
        for(int i=1;i<FF_NP_PEERS;++i) {
            FF_Peer *peer=&np->peers[i];if(!peer->used) continue;
            uint32_t quiet=now-peer->heard;
            if(np->phase==FF_NP_LOBBY&&quiet>5000) {drop_peer(np,i);continue;}
            if(np->phase==FF_NP_PLAYING&&quiet>8000) {end(np,"A PLAYER LOST CONNECTION");return;}
            if(tick&&np->phase==FF_NP_LOBBY) lobby_packet(np,peer->addr);
            if(tick&&np->phase==FF_NP_PLAYING&&!peer->started) start_packet(np,peer->addr);
        }
        if(tick&&np->phase==FF_NP_LOBBY) for(int i=0;i<np->punch_count;++i)
            if((int32_t)(np->punch_until[i]-now)>0) send_type(np,np->punch[i],PUNCH,NULL,0);
    } else {
        uint32_t quiet=now-np->peers[0].heard;
        if(quiet>(np->me<0?20000u:8000u)) {end(np,np->me<0?"NO ANSWER FROM THE HOST":"LOST CONNECTION TO THE HOST");return;}
        if(tick&&np->me<0) {
            uint8_t b[9]={(uint8_t)np->local_count};put32(b+1,np->arena_hash);put32(b+5,np->nonce);
            send_type(np,np->direct,HELLO,b,9);
            /* Same home network: the router may not loop public addresses back, so ask the LAN too. */
            send_type(np,(FF_Addr){0xFFFFFFFFu,np->direct.port},HELLO,b,9);
            if(np->direct.port!=FF_NET_PORT) send_type(np,(FF_Addr){0xFFFFFFFFu,FF_NET_PORT},HELLO,b,9);
        }
    }
}
void ff_np_send(FF_Netplay *np) {
    ff_np_poll(np);
    if(np->phase==FF_NP_PLAYING) for(int i=0;i<FF_NP_PEERS;++i) if(i!=np->me&&np->peers[i].used) send_input(np,i);
}
unsigned ff_np_tick(FF_Netplay *np,const uint8_t local[FF_PLAYERS]) {
    ff_np_poll(np);
    if(np->phase!=FF_NP_PLAYING) return 0;
    uint8_t keys[FF_PLAYERS]={0};
    for(int i=0;i<np->local_count;++i) {int s=ff_np_seat_of_local(np,i);if(s>=0) keys[s]=local[i];}
    /* The machine that runs ahead waits a tick now and then, so nobody has to roll back far. */
    bool ahead=false;
    for(int i=0;i<FF_NP_PEERS;++i) {
        const FF_Peer *peer=&np->peers[i];
        if(i==np->me||!peer->used||!peer->started) continue;
        int mine=(int)np->rb.frame-(int)peer->frame;
        if(mine-peer->advantage>=3) ahead=true;
    }
    unsigned sounds=0;bool advanced=false;
    if(!(ahead&&np->rb.frame-np->last_stall>=6)) {
        if(ff_rb_can_take_local(&np->rb)) ff_rb_local(&np->rb,keys);
        advanced=ff_rb_advance(&np->rb,np->arena,&sounds);
    } else np->last_stall=np->rb.frame;
    np->stalled=advanced?0:np->stalled+1;
    for(int i=0;i<FF_NP_PEERS;++i) if(i!=np->me&&np->peers[i].used) send_input(np,i);
    return sounds;
}
void ff_np_close(FF_Netplay *np) {
    if(np->phase==FF_NP_OFF) return;
    for(int k=0;k<3;++k) for(int i=0;i<FF_NP_PEERS;++i) if(i!=np->me&&np->peers[i].used&&np->peers[i].addr.ip) {
        /* QUIT goes out undelayed even under a simulated bad line. */
        uint8_t p[HEADER];header(p,QUIT,np->token);int loss=np->udp.loss,delay=np->udp.delay,jitter=np->udp.jitter;
        np->udp.loss=np->udp.delay=np->udp.jitter=0;ff_udp_send(&np->udp,np->peers[i].addr,p,HEADER);
        np->udp.loss=loss;np->udp.delay=delay;np->udp.jitter=jitter;
    }
    if(np->http_busy) ff_http_close(&np->http);
    ff_udp_close(&np->udp);np->phase=FF_NP_OFF;
}
