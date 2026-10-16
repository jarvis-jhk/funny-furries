#include "rollback.h"
#include <string.h>
#define SLOT(f) ((f)%FF_RB_RING)
static bool in_match(const FF_Rollback *rb,int seat) {return (rb->seats>>seat)&1u;}
void ff_rb_init(FF_Rollback *rb,const FF_Game *start,unsigned seats,unsigned local,int delay) {
    memset(rb,0,sizeof(*rb));
    rb->state=*start;rb->seats=seats;rb->local=local&seats;
    rb->delay=delay<0?0:delay>FF_RB_MAX_DELAY?FF_RB_MAX_DELAY:delay;
    /* Nobody has pressed anything during the input delay, so those frames are known everywhere. */
    for(int s=0;s<FF_PLAYERS;++s) rb->confirmed[s]=(uint32_t)rb->delay;
    rb->rollback_to=UINT32_MAX;rb->desync=UINT32_MAX;
}
uint32_t ff_rb_settled(const FF_Rollback *rb) {
    uint32_t low=UINT32_MAX;
    for(int s=0;s<FF_PLAYERS;++s) if(in_match(rb,s)&&rb->confirmed[s]<low) low=rb->confirmed[s];
    return low==UINT32_MAX?rb->frame+(uint32_t)rb->delay:low;
}
bool ff_rb_input(FF_Rollback *rb,int seat,uint32_t frame,uint8_t keys) {
    if(seat<0||seat>=FF_PLAYERS||!in_match(rb,seat)) return false;
    if(frame<rb->confirmed[seat]) return true;
    if(frame>rb->confirmed[seat]||frame>=ff_rb_settled(rb)+FF_RB_RING-1) return false;
    rb->input[SLOT(frame)][seat]=keys;rb->confirmed[seat]=frame+1;
    if(frame<rb->frame&&rb->used[SLOT(frame)][seat]!=keys&&frame<rb->rollback_to) rb->rollback_to=frame;
    return true;
}
bool ff_rb_can_take_local(const FF_Rollback *rb) {
    for(int s=0;s<FF_PLAYERS;++s) if((rb->local>>s)&1u) return rb->confirmed[s]<=rb->frame+(uint32_t)rb->delay;
    return false;
}
void ff_rb_local(FF_Rollback *rb,const uint8_t keys[FF_PLAYERS]) {
    for(int s=0;s<FF_PLAYERS;++s) if((rb->local>>s)&1u)
        while(rb->confirmed[s]<=rb->frame+(uint32_t)rb->delay) ff_rb_input(rb,s,rb->confirmed[s],keys[s]);
}
static void inputs_for(const FF_Rollback *rb,uint32_t frame,uint8_t keys[FF_PLAYERS]) {
    for(int s=0;s<FF_PLAYERS;++s) {
        if(!in_match(rb,s)) keys[s]=0;
        else if(frame<rb->confirmed[s]) keys[s]=rb->input[SLOT(frame)][s];
        /* A remote player most likely still holds what they held last. */
        else keys[s]=rb->confirmed[s]?rb->input[SLOT(rb->confirmed[s]-1)][s]:0;
    }
}
static void simulate(FF_Rollback *rb,const FF_Arena *a) {
    uint32_t f=rb->frame;
    rb->snap[SLOT(f)]=rb->state;
    inputs_for(rb,f,rb->used[SLOT(f)]);
    ff_game_tick(&rb->state,a,rb->used[SLOT(f)]);
    rb->frame=f+1;
}
static void record_checks(FF_Rollback *rb) {
    uint32_t settled=ff_rb_settled(rb);
    while(rb->next_check<=settled&&rb->next_check<=rb->frame) {
        uint32_t f=rb->next_check;
        uint32_t hash=f==rb->frame?ff_game_hash(&rb->state):ff_game_hash(&rb->snap[SLOT(f)]);
        unsigned slot=(f/FF_RB_CHECK)%16u;rb->check_frame[slot]=f;rb->check_hash[slot]=hash;
        rb->next_check+=FF_RB_CHECK;
    }
}
bool ff_rb_advance(FF_Rollback *rb,const FF_Arena *a,unsigned *sounds) {
    if(sounds) *sounds=0;
    if(rb->rollback_to<rb->frame) {
        uint32_t end=rb->frame;
        rb->state=rb->snap[SLOT(rb->rollback_to)];rb->frame=rb->rollback_to;
        rb->resimulated+=end-rb->frame;++rb->rollbacks;
        while(rb->frame<end) simulate(rb,a);
    }
    rb->rollback_to=UINT32_MAX;
    record_checks(rb);
    if(rb->frame>=ff_rb_settled(rb)+FF_RB_PREDICT) return false;
    for(int s=0;s<FF_PLAYERS;++s) if(((rb->local>>s)&1u)&&rb->confirmed[s]<=rb->frame) return false;
    simulate(rb,a);
    if(rb->frame>rb->sounded) {if(sounds) *sounds=rb->state.sounds;rb->sounded=rb->frame;}
    record_checks(rb);
    return true;
}
bool ff_rb_last_check(const FF_Rollback *rb,uint32_t *frame,uint32_t *hash) {
    if(!rb->next_check) return false;
    uint32_t f=rb->next_check-FF_RB_CHECK;unsigned slot=(f/FF_RB_CHECK)%16u;
    *frame=rb->check_frame[slot];*hash=rb->check_hash[slot];return true;
}
void ff_rb_remote_check(FF_Rollback *rb,uint32_t frame,uint32_t hash) {
    if(frame%FF_RB_CHECK||frame>=rb->next_check) return;
    unsigned slot=(frame/FF_RB_CHECK)%16u;
    if(rb->check_frame[slot]==frame&&rb->check_hash[slot]!=hash&&frame<rb->desync) rb->desync=frame;
}
