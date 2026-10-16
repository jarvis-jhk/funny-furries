#include "rollback.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
/* Held controls that change every few frames, like a person playing. */
static uint8_t script(int seat,uint32_t frame) {
    uint32_t x=(frame/7u)*2654435761u^(uint32_t)(seat+1)*40503u;x^=x>>13;x*=0x5bd1e995u;x^=x>>15;
    uint8_t keys=(uint8_t)(x&63u);
    if((keys&(FF_LEFT|FF_RIGHT))==(FF_LEFT|FF_RIGHT)) keys&=(uint8_t)~FF_LEFT;
    return keys;
}
static uint32_t rng=12345;
static uint32_t roll(uint32_t n) {rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng%n;}
#define MACHINES 4
#define FLIGHT 4096
typedef struct {int to,seat;uint32_t first,count,at;uint8_t keys[48];} Packet;
static Packet flight[FLIGHT];static int in_flight;
static FF_Rollback machines[MACHINES];
static uint32_t reference_hash(const FF_Game *start,unsigned seats,int delay,uint32_t frames) {
    FF_Game g=*start;
    for(uint32_t f=0;f<frames;++f) {
        uint8_t in[FF_PLAYERS]={0};
        for(int s=0;s<FF_PLAYERS;++s) if(((seats>>s)&1u)&&f>=(uint32_t)delay) in[s]=script(s,f-(uint32_t)delay);
        ff_game_tick(&g,&arena,in);
    }
    return ff_game_hash(&g);
}
/* owner[seat] is the machine playing that seat; loss is in percent, latency in steps. */
static void network_match(int count,const int owner[FF_PLAYERS],unsigned seats,int mode,int delay,int loss,int latency,int jitter,uint32_t target) {
    FF_Game start;ff_game_setup(&start,&arena,777,seats,mode);
    for(int m=0;m<count;++m) {
        unsigned local=0;for(int s=0;s<FF_PLAYERS;++s) if(owner[s]==m) local|=1u<<s;
        ff_rb_init(&machines[m],&start,seats,local,delay);
    }
    in_flight=0;uint32_t now=0;
    for(;;++now) {
        CHECK(now<target*20);
        bool finished=true;
        for(int m=0;m<count;++m) if(ff_rb_settled(&machines[m])<target+FF_RB_CHECK) finished=false;
        if(finished) break;
        /* Deliver what has arrived; late copies and duplicates are harmless. */
        for(int i=0;i<in_flight;) {
            Packet *p=&flight[i];
            if(p->at<=now) {
                for(uint32_t k=0;k<p->count;++k) ff_rb_input(&machines[p->to],p->seat,p->first+k,p->keys[k]);
                flight[i]=flight[--in_flight];
            } else ++i;
        }
        for(int m=0;m<count;++m) {
            FF_Rollback *rb=&machines[m];
            /* Machines run at slightly different speeds. */
            if(roll(100)<8) continue;
            if(rb->frame<target+2*FF_RB_CHECK) {
                uint8_t keys[FF_PLAYERS]={0};
                for(int s=0;s<FF_PLAYERS;++s) keys[s]=script(s,rb->frame);
                if(ff_rb_can_take_local(rb)) ff_rb_local(rb,keys);
                ff_rb_advance(rb,&arena,NULL);
            }
            for(int s=0;s<FF_PLAYERS;++s) if(owner[s]==m) for(int to=0;to<count;++to) if(to!=m) {
                if(roll(100)<(uint32_t)loss||in_flight==FLIGHT) continue;
                /* Resend the recent history every time, so a lost packet costs nothing. */
                uint32_t end=rb->confirmed[s],first=end>40?end-40:0;
                Packet *p=&flight[in_flight++];p->to=to;p->seat=s;p->first=first;p->count=end-first;
                p->at=now+(uint32_t)latency+roll((uint32_t)jitter+1);
                for(uint32_t k=0;k<p->count;++k) p->keys[k]=rb->input[(first+k)%FF_RB_RING][s];
            }
            uint32_t frame,hash;
            if(ff_rb_last_check(rb,&frame,&hash)) for(int to=0;to<count;++to) ff_rb_remote_check(&machines[to],frame,hash);
        }
    }
    uint32_t expect=reference_hash(&start,seats,delay,target);unsigned rollbacks=0;
    for(int m=0;m<count;++m) {
        const FF_Rollback *rb=&machines[m];unsigned slot=(target/FF_RB_CHECK)%16u;
        CHECK(rb->check_frame[slot]==target);CHECK(rb->check_hash[slot]==expect);
        CHECK(rb->desync==UINT32_MAX);rollbacks+=rb->rollbacks;
    }
    if(latency+jitter>delay) CHECK(rollbacks>0);
    printf("machines=%d delay=%d loss=%d%% latency=%d+%d frames=%u rollbacks=%u hash=%08x\n",count,delay,loss,latency,jitter,target,rollbacks,expect);
}
static void desync_detected(void) {
    FF_Game start;ff_game_setup(&start,&arena,5,3,FF_FFA);
    FF_Rollback a,b;ff_rb_init(&a,&start,3,1,0);ff_rb_init(&b,&start,3,2,0);
    b.state.players[1].health=99;  /* simulate a diverging machine */
    for(uint32_t f=0;f<100;++f) {
        uint8_t keys[FF_PLAYERS]={FF_RIGHT,FF_LEFT};
        ff_rb_local(&a,keys);ff_rb_local(&b,keys);
        ff_rb_input(&a,1,f,FF_LEFT);ff_rb_input(&b,0,f,FF_RIGHT);
        ff_rb_advance(&a,&arena,NULL);ff_rb_advance(&b,&arena,NULL);
        uint32_t frame,hash;
        if(ff_rb_last_check(&b,&frame,&hash)) ff_rb_remote_check(&a,frame,hash);
    }
    CHECK(a.desync!=UINT32_MAX);
}
static void prediction_limit(void) {
    FF_Game start;ff_game_setup(&start,&arena,5,3,FF_FFA);FF_Rollback rb;ff_rb_init(&rb,&start,3,1,2);
    uint8_t keys[FF_PLAYERS]={0};int advanced=0;
    for(int i=0;i<100;++i) {if(ff_rb_can_take_local(&rb)) ff_rb_local(&rb,keys);advanced+=ff_rb_advance(&rb,&arena,NULL);}
    CHECK(advanced==2+FF_RB_PREDICT);
    CHECK(!ff_rb_input(&rb,1,5,0));CHECK(ff_rb_input(&rb,1,2,FF_JUMP));CHECK(rb.rollback_to==2);
    CHECK(ff_rb_advance(&rb,&arena,NULL));CHECK(rb.rollbacks==1);
}
int main(void) {
    ff_arena_practice(&arena);
    prediction_limit();desync_detected();
    int two[FF_PLAYERS]={0,1,-1,-1},three[FF_PLAYERS]={0,1,2,2},four[FF_PLAYERS]={0,1,2,3};
    network_match(2,two,3,FF_FFA,2,0,1,0,3008);
    network_match(2,two,3,FF_FFA,2,25,4,6,3008);
    network_match(2,two,3,FF_FFA,0,40,6,8,2016);
    network_match(3,three,15,FF_FFA,2,20,3,5,3008);
    network_match(4,four,15,FF_TEAMS,3,30,5,7,3008);
    printf("rollback checks=%u\n",checks);
    return 0;
}
