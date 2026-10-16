/* Headless online player for tests: hosts or joins over real UDP sockets,
 * plays scripted controls and prints the checksum of one confirmed frame. */
#include "netplay.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
static void pause_ms(int ms) {Sleep((DWORD)ms);}
#else
#include <time.h>
static void pause_ms(int ms) {struct timespec t={0,ms*1000000L};nanosleep(&t,NULL);}
#endif
static uint8_t script(int seat,uint32_t frame) {
    uint32_t x=(frame/7u)*2654435761u^(uint32_t)(seat+1)*40503u;x^=x>>13;x*=0x5bd1e995u;x^=x>>15;
    uint8_t keys=(uint8_t)(x&63u);
    if((keys&(FF_LEFT|FF_RIGHT))==(FF_LEFT|FF_RIGHT)) keys&=(uint8_t)~FF_LEFT;
    return keys;
}
static FF_Arena arena;static FF_Netplay np;
int main(int argc,char **argv) {
    if(argc<2||(argc<4&&strcmp(argv[1],"internet"))) {fprintf(stderr,"net_probe internet | host PORT SEATS ffa|teams FRAMES [LOCAL] | join ADDRESS FRAMES [LOCAL] | offline SEATS ffa|teams FRAMES\n");return 2;}
    ff_arena_practice(&arena);
    int ms=getenv("FF_PROBE_MS")?atoi(getenv("FF_PROBE_MS")):20;
    bool host=!strcmp(argv[1],"host"),offline=!strcmp(argv[1],"offline");
    if(!strcmp(argv[1],"internet")) {
        /* Live check of the outside helpers: STUN answer and an ntfy round trip. Not run in CI. */
        if(!ff_np_host(&np,&arena,1,0,true)) return 1;
        uint32_t began=ff_net_ms();
        while(!np.have_public&&ff_net_ms()-began<6000) {ff_np_poll(&np);pause_ms(20);}
        printf("public=%d code=%s relay=%d topic=%s\n",np.have_public,np.code,np.relay_ok,np.topic);
        if(!np.have_public||!np.relay_ok) return 1;
        char request[256],body[]="203.0.113.9:4567";FF_Http h;
        snprintf(request,sizeof(request),"POST /%s HTTP/1.0\r\nHost: ntfy.sh\r\nContent-Length: %u\r\n\r\n%s",np.topic,(unsigned)strlen(body),body);
        ff_http_start(&h,np.relay,request);int r;while(!(r=ff_http_poll(&h))) pause_ms(20);
        printf("post=%d\n",r);pause_ms(1500);
        began=ff_net_ms();
        while(!np.punch_count&&ff_net_ms()-began<10000) {ff_np_poll(&np);pause_ms(20);}
        char text[32]="";if(np.punch_count) ff_addr_text(np.punch[0],text,sizeof(text));
        printf("host learned guest address: %s\n",text);ff_np_close(&np);
        return strcmp(text,body)!=0;
    }
    if(offline) {
        int seats=atoi(argv[2]);uint32_t frames=(uint32_t)atoi(argv[4]);FF_Game g;
        ff_game_setup(&g,&arena,4242,(1u<<seats)-1,!strcmp(argv[3],"teams")?FF_TEAMS:FF_FFA);
        for(uint32_t f=0;f<frames;++f) {
            uint8_t in[FF_PLAYERS]={0};
            for(int s=0;s<seats;++s) if(f>=FF_NP_DELAY) in[s]=script(s,f-FF_NP_DELAY);
            ff_game_tick(&g,&arena,in);
        }
        printf("frame=%u hash=%08x\n",frames,ff_game_hash(&g));return 0;
    }
    int expect=0,mode=FF_FFA,local=1;uint32_t target;
    if(host) {
        if(argc<6) return 2;
        expect=atoi(argv[3]);mode=!strcmp(argv[4],"teams")?FF_TEAMS:FF_FFA;target=(uint32_t)atoi(argv[5]);
        if(argc>6) local=atoi(argv[6]);
        if(!ff_np_host(&np,&arena,local,(uint16_t)atoi(argv[2]),false)) {fprintf(stderr,"%s\n",np.status);return 1;}
        printf("code=%s lan=%s\n",np.code,np.lan_text);fflush(stdout);
    } else {
        target=(uint32_t)atoi(argv[3]);if(argc>4) local=atoi(argv[4]);
        if(!ff_np_join(&np,&arena,argv[2],local,false)) {fprintf(stderr,"%s\n",np.status);return 1;}
    }
    target-=target%FF_RB_CHECK;
    uint32_t began=ff_net_ms(),done_at=0,hash=0;
    for(;;) {
        if(ff_net_ms()-began>120000) {fprintf(stderr,"timeout: %s\n",np.status);return 1;}
        if(np.phase==FF_NP_ENDED&&!done_at) {fprintf(stderr,"ended: %s\n",np.ended);return 1;}
        if(np.phase==FF_NP_LOBBY) {
            ff_np_poll(&np);
            int n=0;for(int s=0;s<FF_PLAYERS;++s) n+=(np.seats>>s)&1u;
            if(host&&n==expect) ff_np_start(&np,mode,4242);
        } else if(np.phase==FF_NP_PLAYING) {
            if(done_at) {
                ff_np_send(&np);
                if(ff_net_ms()-done_at>3000) break;
            } else {
                if(np.rb.frame<target+2*FF_RB_CHECK) {
                    uint8_t keys[FF_PLAYERS]={0};
                    for(int i=0;i<np.local_count&&i<FF_PLAYERS;++i) keys[i]=script(ff_np_seat_of_local(&np,i),np.rb.frame);
                    ff_np_tick(&np,keys);
                } else ff_np_send(&np);
                if(np.rb.desync!=UINT32_MAX) {fprintf(stderr,"desync at frame %u\n",np.rb.desync);return 1;}
                if(ff_rb_settled(&np.rb)>=target+FF_RB_CHECK) {
                    unsigned slot=(target/FF_RB_CHECK)%16u;
                    if(np.rb.check_frame[slot]!=target) {fprintf(stderr,"lost checksum\n");return 1;}
                    hash=np.rb.check_hash[slot];done_at=ff_net_ms();
                }
            }
        } else if(done_at) break;
        pause_ms(ms);
    }
    printf("frame=%u hash=%08x rollbacks=%u resimulated=%u seats=%u local=%u\n",target,hash,np.rb.rollbacks,np.rb.resimulated,np.seats,np.local_seats);
    ff_np_close(&np);return 0;
}
