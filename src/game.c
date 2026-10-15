#include "game.h"
#include <string.h>
#include <stdlib.h>

static int clamp(int x,int lo,int hi) { return x<lo?lo:(x>hi?hi:x); }
static uint32_t random_word(FF_Game *g) {
    uint32_t x=g->rng; x^=x<<13; x^=x>>17; x^=x<<5; return g->rng=x;
}
static int floor_pixel(int32_t x) {return x>=0?x/FF_FP:-(((-x)+FF_FP-1)/FF_FP);}
static int tile(const FF_Arena *a,int x,int y) {
    if(x<0||x>=FF_W||y<0) return FF_SOLID;
    if(y>=FF_ROWS*FF_TILE) return 0;
    return a->imported?(y<FF_H?a->mask[y][x]:0):a->tiles[y/FF_TILE][x/FF_TILE];
}
static bool blocked(const FF_Arena *a,int x,int y) {
    if(x-11<0||x+10>=FF_W||y-26<0) return true;
    /* Union of the original head, wall and lower-body sensor silhouettes. */
    for(int yy=y-26;yy<y;++yy) {
        int half=yy>=y-21&&yy<y-8?11:7;
        for(int xx=x-half;xx<x+half;++xx) if(tile(a,xx,yy)==FF_SOLID) return true;
    }
    return false;
}
static bool supported(const FF_Arena *a,int x,int y) {
    for(int xx=x-9;xx<x+9;++xx)
        if(tile(a,xx,y)==FF_PLATFORM&&tile(a,xx,y-1)!=FF_PLATFORM) return true;
    return false;
}
static FF_Point spawn(FF_Game *g,const FF_Arena *a,int who) {
    int start=(int)(random_word(g)%(uint32_t)a->spawn_count);
    FF_Point result=a->spawns[start];
    const FF_Player *other=&g->players[1-who];
    for(int i=0;i<a->spawn_count;++i) {
        FF_Point p=a->spawns[(start+i)%a->spawn_count];
        if(!blocked(a,p.x,p.y)&&abs(p.x-other->x/FF_FP)+abs(p.y-other->y/FF_FP)>100) return p;
    }
    return result;
}
static void reset_player(FF_Player *p,FF_Point pos,int who) {
    int lives=p->lives, score=p->score;
    memset(p,0,sizeof(*p));p->lives=lives;p->score=score;
    p->x=pos.x*FF_FP;p->y=pos.y*FF_FP;p->health=100;p->facing=who?-1:1;
    p->invulnerable=50;
}
void ff_game_init(FF_Game *g,const FF_Arena *a,uint32_t seed) {
    memset(g,0,sizeof(*g));g->rng=seed?seed:1;g->winner=-1;g->trap_wait=400+(int)(random_word(g)%400);
    for(int i=0;i<2;++i) {
        g->players[i].lives=3;
        reset_player(&g->players[i],a->spawns[i%a->spawn_count],i);
    }
    g->pickup_wait=300+(int)(random_word(g)%300);
    int count=a->imported?0:(a->spawn_count<8?a->spawn_count:8);
    for(int i=0;i<count;++i) {
        FF_Point p=a->spawns[i];
        g->pickups[i]=(FF_Pickup){p.x,p.y-16,1+i%5,1,0};
    }
}
static void move_player(FF_Player *p,const FF_Arena *a) {
    int32_t next=p->x+p->vx;
    int old=floor_pixel(p->x), target=floor_pixel(next), y=floor_pixel(p->y);
    int step=p->vx<0?-1:1;
    for(int x=old;x!=target;) {
        x+=step;
        if(blocked(a,x,y)) {next=(x-step)*FF_FP;p->vx=0;break;}
    }
    p->x=next;
    int x=floor_pixel(p->x);next=p->y+p->vy;
    old=floor_pixel(p->y);target=floor_pixel(next);step=p->vy<0?-1:1;
    p->grounded=0;
    for(int yy=old;yy!=target;) {
        yy+=step;bool hit=blocked(a,x,yy);
        if(step>0) {
            /* One-way tops catch only a crossing from above. */
            if(supported(a,x,yy-1)) hit=true;
        }
        if(hit) {next=(yy-step)*FF_FP;p->vy=0;p->grounded=step>0;break;}
    }
    p->y=next;
    if(!p->grounded&&p->vy>=0) {
        y=floor_pixel(p->y);
        p->grounded=blocked(a,x,y+1)||supported(a,x,y);
    }
    if(p->grounded) {p->y=floor_pixel(p->y)*FF_FP;p->vy=0;}
}
FF_Point ff_device_position(const FF_Arena *a,int device,uint32_t tick) {
    const FF_Device *d=&a->devices[device];
    if(d->kind!=FF_MOVING_PLATFORM) return (FF_Point){d->x,d->y};
    const FF_Path *path=&a->paths[device];
    int lo=path->speed?path->min_x:d->x,hi=path->speed?path->max_x:d->x+128;
    int speed=path->speed?path->speed:2,dir=path->speed?path->direction:1;
    uint32_t span=(uint32_t)(hi-lo),period=2*span;
    uint32_t phase=(uint32_t)(dir<0?period-(uint32_t)(d->x-lo):(uint32_t)(d->x-lo));
    phase=(phase+(tick%period)*(uint32_t)speed)%period;
    return (FF_Point){lo+(int)(phase<=span?phase:period-phase),d->y};
}
static bool underwater(const FF_Player *p,const FF_Arena *a) {
    int x=p->x/FF_FP,y=p->y/FF_FP-16;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(d->kind==FF_WATER&&x>=d->x&&x<d->x+d->w&&y>=d->y&&y<560) return true;
    }
    return false;
}
static bool overlaps(int x,int y,int w,int h,const FF_Device *d) {
    return x<d->x+d->w&&x+w>d->x&&y<d->y+d->h&&y+h>d->y;
}
static void device_forces(FF_Player *p,const FF_Arena *a) {
    int x=p->x/FF_FP,feet=p->y/FF_FP,y=feet-16;
    if(p->bounce_wait) --p->bounce_wait;
    bool wind_volumes=false;
    for(int i=0;i<a->device_count;++i) if(a->devices[i].kind>=FF_WIND_LEFT) wind_volumes=true;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(!wind_volumes&&d->kind==FF_FAN_UP&&x>=d->x&&x<d->x+d->w&&y>d->y-110&&y<d->y+12) p->vy=clamp(p->vy-FF_FP/2,-5*FF_FP,8*FF_FP);
        if(!wind_volumes&&d->kind==FF_FAN_LEFT&&y>=d->y&&y<d->y+d->h&&x>d->x-110&&x<d->x+12) p->vx=clamp(p->vx-FF_FP/2,-6*FF_FP,6*FF_FP);
        if(!wind_volumes&&d->kind==FF_FAN_RIGHT&&y>=d->y&&y<d->y+d->h&&x>d->x-12&&x<d->x+110) p->vx=clamp(p->vx+FF_FP/2,-6*FF_FP,6*FF_FP);
        bool in_wind=d->kind==FF_WIND_UP?overlaps(x-9,feet-8,18,9,d):overlaps(x-7,feet-16,14,16,d);
        if(d->kind>=FF_WIND_LEFT&&in_wind) {
            if(d->kind==FF_WIND_UP) p->vy=clamp(p->vy-5*FF_FP/8,-100*FF_FP/8,100*FF_FP/8);
            else p->vx=clamp(p->vx+(d->kind==FF_WIND_LEFT?-5:5)*FF_FP/8,-100*FF_FP/8,100*FF_FP/8);
        }
        if(p->bounce_wait||d->kind<FF_BOUNCE_UP||d->kind>FF_BOUNCE_RIGHT) continue;
        bool touching=d->kind==FF_BOUNCE_UP?overlaps(x-9,feet-8,18,9,d):
            d->kind==FF_BOUNCE_DOWN?overlaps(x-7,feet-26,14,12,d):
            d->kind==FF_BOUNCE_LEFT?overlaps(x+4,feet-21,8,13,d):overlaps(x-12,feet-21,8,13,d);
        if(!touching) continue;
        if(d->kind==FF_BOUNCE_UP&&p->vy>0) p->vy=-clamp(p->vy+20*FF_FP/8,0,100*FF_FP/8);
        else if(d->kind==FF_BOUNCE_DOWN&&p->vy<0) p->vy=100*FF_FP/8;
        else if(d->kind==FF_BOUNCE_LEFT&&p->vx>0) p->vx=-100*FF_FP/8;
        else if(d->kind==FF_BOUNCE_RIGHT&&p->vx<0) p->vx=100*FF_FP/8;
        else continue;
        p->grounded=0;p->bounce_wait=2;
    }
}
static void platform_carry(FF_Player *p,const FF_Arena *a,uint32_t tick) {
    if(!p->grounded) return;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];if(d->kind!=FF_MOVING_PLATFORM) continue;
        FF_Point old=ff_device_position(a,i,tick-1),now=ff_device_position(a,i,tick);
        int x=p->x/FF_FP,y=p->y/FF_FP;
        if(y==old.y&&x+8>=old.x&&x-9<old.x+d->w) {
            int next=x+now.x-old.x;
            if(!blocked(a,next,y)) p->x+=FF_FP*(now.x-old.x);
        }
    }
}
static void platform_land(FF_Player *p,const FF_Arena *a,uint32_t tick,int32_t old_y) {
    if(p->vy<0) return;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];if(d->kind!=FF_MOVING_PLATFORM) continue;
        FF_Point now=ff_device_position(a,i,tick);int x=p->x/FF_FP;
        if(old_y<=now.y*FF_FP&&p->y>=now.y*FF_FP&&x+8>=now.x&&x-9<now.x+d->w) {
            p->y=now.y*FF_FP;p->vy=0;p->grounded=1;
        }
    }
}
static void shoot(FF_Game *g,FF_Player *p,int owner) {
    if(p->weapon==FF_FISTS||p->ammo<=0||p->cooldown) return;
    for(int i=0;i<FF_SHOTS;++i) if(!g->shots[i].life) {
        int kind=p->weapon;
        g->shots[i]=(FF_Shot){p->x+p->facing*16*FF_FP,p->y-18*FF_FP,
            p->facing*(kind==FF_ICE?100:kind==FF_ROCKET?57:40)*FF_FP/8,0,kind,owner,kind==FF_FLAME?270:100,p->facing<0?16:0,0};
        --p->ammo;p->cooldown=kind==FF_ROCKET?50:8;
        g->sounds|=kind==FF_ICE?FF_SOUND_ICE:kind==FF_ROCKET?FF_SOUND_ROCKET:FF_SOUND_FLAME;
        if(!p->ammo) p->weapon=FF_FISTS;
        return;
    }
}
/* CnC direction 0 is right and 8 is up. Fixed vectors keep replay portable. */
static const int direction_x[32]={256,251,237,213,181,142,98,50,0,-50,-98,-142,-181,-213,-237,-251,
                                 -256,-251,-237,-213,-181,-142,-98,-50,0,50,98,142,181,213,237,251};
static int direction_y(int direction) {return -direction_x[(direction+24)&31];}
static int toward(int32_t dx,int32_t dy) {
    int best=0;int64_t score=INT64_MIN;
    for(int i=0;i<32;++i) {
        int64_t dot=(int64_t)dx*direction_x[i]+(int64_t)dy*direction_y(i);
        if(dot>score) {score=dot;best=i;}
    }
    return best;
}
static int turn(int direction,int target) {
    int delta=(target-direction+32)&31;
    if(delta) direction=(direction+(delta<=16?1:31))&31;
    return direction;
}
static void rocket_steer(FF_Shot *s,const FF_Game *g,const FF_Arena *a) {
    const FF_Player *target=&g->players[1-s->owner];
    if(!target->respawn&&target->health>0)
        s->direction=turn(s->direction,toward(target->x-s->x,target->y-16*FF_FP-s->y));
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(d->kind<FF_WIND_LEFT||s->x<d->x*FF_FP||s->x>=(d->x+d->w)*FF_FP||
           s->y<d->y*FF_FP||s->y>=(d->y+d->h)*FF_FP) continue;
        s->direction=turn(s->direction,d->kind==FF_WIND_UP?8:d->kind==FF_WIND_LEFT?16:0);
    }
    s->vx=direction_x[s->direction]*57/8;s->vy=direction_y(s->direction)*57/8;
}
static void blast(FF_Game *g,int32_t x,int32_t y) {
    for(int i=0;i<FF_BLASTS;++i) if(!g->blasts[i].life) {
        g->blasts[i]=(FF_Blast){x,y,20,0};g->sounds|=FF_SOUND_BLAST;return;
    }
}
static bool near(int32_t x,int32_t y,int32_t other_x,int32_t other_y,int radius) {
    return abs(x-other_x)<radius*FF_FP&&abs(y-other_y)<radius*FF_FP;
}
static void hazard_spawn(FF_Game *g,const FF_Arena *a) {
    if(!a->bonus_count||--g->trap_wait>0) return;
    g->trap_wait=200+(int)(random_word(g)%900);
    for(int i=0;i<FF_HAZARDS;++i) if(!g->hazards[i].life) {
        FF_Point p=a->bonuses[random_word(g)%(uint32_t)a->bonus_count];
        int kind=1+(int)(random_word(g)%3),dir=(random_word(g)&1)?1:-1;
        g->hazards[i]=(FF_Hazard){p.x*FF_FP,p.y*FF_FP,kind==FF_BOMB?0:dir*FF_FP,0,kind,1500,0};
        return;
    }
}
static void hazard_tick(FF_Game *g,const FF_Arena *a,int damage[2]) {
    hazard_spawn(g,a);
    for(int i=0;i<FF_HAZARDS;++i) {
        FF_Hazard *h=&g->hazards[i];if(!h->life) continue;
        if(--h->life==0) continue;
        int x=floor_pixel(h->x),y=floor_pixel(h->y);
        if(h->kind==FF_BOMB_FLY) {
            int next=floor_pixel(h->x+h->vx);
            if(next<8||next>792||tile(a,next,y)==FF_SOLID) h->vx=-h->vx;
            else h->x+=h->vx;
        } else {
            if(h->kind==FF_BOMB_WALK) {
                int next=floor_pixel(h->x+h->vx),ahead=next+(h->vx<0?-7:7);
                if(next<6||next>794||tile(a,ahead,y-5)==FF_SOLID||
                   (h->grounded&&!tile(a,ahead,y+1))) h->vx=-h->vx;
                else h->x+=h->vx;
            }
            h->vy=clamp(h->vy+FF_FP/4,-6*FF_FP,6*FF_FP);
            int32_t next_y=h->y+h->vy;
            int target=floor_pixel(next_y),step=h->vy<0?-1:1;
            h->grounded=0;x=floor_pixel(h->x);
            for(int yy=y;yy!=target;) {
                yy+=step;int terrain=tile(a,x,yy);
                if(terrain==FF_SOLID||(step>0&&terrain==FF_PLATFORM)) {
                    if(h->kind==FF_BOMB&&terrain==FF_SOLID) {blast(g,h->x,yy*FF_FP);h->life=0;}
                    else {next_y=(yy-step)*FF_FP;h->vy=h->kind==FF_BOMB?-4*FF_FP:0;h->grounded=1;}
                    break;
                }
            }
            h->y=next_y;
        }
        if(h->y>FF_H*FF_FP||h->y<0) {h->life=0;continue;}
        bool contact=false;
        for(int k=0;k<2&&h->life;++k) {
            FF_Player *p=&g->players[k];if(p->respawn) continue;
            if(near(h->x,h->y,p->x,p->y-16*FF_FP,20)) {
                damage[k]+=8;contact=true;
            }
        }
        if(contact) {blast(g,h->x,h->y);h->life=0;}
    }
}
static void blast_tick(FF_Game *g,int damage[2],int knock[2],int lift[2]) {
    /* A bounded repeat propagates chains regardless of the hazard slot order. */
    for(int pass=0;pass<FF_HAZARDS;++pass) {
        bool changed=false;
        for(int i=0;i<FF_BLASTS;++i) if(g->blasts[i].life) {
            for(int j=0;j<FF_HAZARDS;++j) {
                FF_Hazard *h=&g->hazards[j];if(!h->life) continue;
                if(near(g->blasts[i].x,g->blasts[i].y,h->x,h->y,42)) {
                    h->life=0;blast(g,h->x,h->y);changed=true;
                }
            }
        }
        if(!changed) break;
    }
    for(int i=0;i<FF_BLASTS;++i) {
        FF_Blast *b=&g->blasts[i];if(!b->life) continue;
        for(int k=0;k<2;++k) {
            FF_Player *p=&g->players[k];if(p->respawn||(b->hit&(1u<<k))) continue;
            if(near(p->x,p->y-16*FF_FP,b->x,b->y,42)) {
                b->hit|=1u<<k;damage[k]+=8;knock[k]=(p->x<b->x?-50:50)*FF_FP/8;
                lift[k]=(p->y-16*FF_FP<b->y?-50:50)*FF_FP/8;
            }
        }
        --b->life;
    }
}
static void pickup_spawn(FF_Game *g,const FF_Arena *a) {
    if(!a->imported||!a->bonus_count||--g->pickup_wait>0) return;
    g->pickup_wait=100+(int)(random_word(g)%900);
    FF_Point p=a->bonuses[random_word(g)%(uint32_t)a->bonus_count];
    for(int i=0;i<FF_PICKUPS;++i) if(g->pickups[i].active&&
        g->pickups[i].x==p.x&&g->pickups[i].y==p.y) return;
    for(int i=0;i<FF_PICKUPS;++i) if(!g->pickups[i].kind) {
        g->pickups[i]=(FF_Pickup){p.x,p.y,1+(int)(random_word(g)%5),1,0};
        g->sounds|=FF_SOUND_PICKUP;return;
    }
}
static void pickup(FF_Player *p,int kind) {
    static const int amount[]={0,25,15,8}, limit[]={0,50,30,16};
    if(kind==FF_HEALTH) p->health=clamp(p->health+25,0,100);
    else if(kind==FF_FUEL) p->fuel=clamp(p->fuel+150,0,300);
    else {p->ammo=clamp((p->weapon==kind?p->ammo:0)+amount[kind],0,limit[kind]);p->weapon=kind;}
}
void ff_game_tick(FF_Game *g,const FF_Arena *a,const uint8_t input[2]) {
    g->sounds=0;++g->tick;
    if(g->winner>=0) {
        if(--g->round_wait<=0) {
            int scores[2]={g->players[0].score,g->players[1].score}; uint32_t rng=g->rng,tick_count=g->tick;
            ff_game_init(g,a,rng);g->tick=tick_count;
            for(int i=0;i<2;++i) g->players[i].score=scores[i];
        }
        return;
    }
    int damage[2]={0}, burning[2]={0}, knock[2]={0}, lift[2]={0};
    for(int i=0;i<2;++i) {
        FF_Player *p=&g->players[i];uint8_t keys=input[i];
        if(p->respawn) {
            if(--p->respawn==0) reset_player(p,spawn(g,a,i),i);
            p->previous=keys;continue;
        }
        if(p->invulnerable) --p->invulnerable;
        if(p->cooldown) --p->cooldown;
        if(p->punch_ticks) --p->punch_ticks;
        if(p->burn_wait) --p->burn_wait;
        bool wet=underwater(p,a);
        platform_carry(p,a,g->tick);
        int horizontal=!!(keys&FF_RIGHT)-!!(keys&FF_LEFT);
        if(horizontal) {
            /* Input cannot erase a stronger bounce or explosion impulse. */
            int speed=p->vx*horizontal,cap=(wet?18:25)*FF_FP/8;
            if(speed<cap) p->vx=horizontal*(speed+FF_FP/2>cap?cap:speed+FF_FP/2);
            else if(speed>cap) p->vx=horizontal*(speed-FF_FP/8<cap?cap:speed-FF_FP/8);
            p->facing=horizontal;
        } else if(p->vx>0) p->vx=p->vx>FF_FP/8?p->vx-FF_FP/8:0;
        else if(p->vx<0) p->vx=p->vx<-FF_FP/8?p->vx+FF_FP/8:0;
        int gravity=wet?FF_FP/8:FF_FP/4,fall_cap=wet?20*FF_FP/8:8*FF_FP;
        if(p->vy>fall_cap) p->vy-=gravity;
        else p->vy=clamp(p->vy+gravity,-100*FF_FP/8,fall_cap);
        if(!wet&&(keys&FF_JUMP)&&!(p->previous&FF_JUMP)&&p->grounded) {p->vy=-44*FF_FP/8;p->grounded=0;}
        if(wet) {
            if((keys&FF_JUMP)&&p->vy>-20*FF_FP/8) p->vy=clamp(p->vy-2*FF_FP/8,-20*FF_FP/8,100*FF_FP/8);
        }
        if((keys&FF_FLY)&&p->fuel) {p->vy=clamp(p->vy-FF_FP/2,-5*FF_FP,8*FF_FP);--p->fuel;}
        device_forces(p,a);
        int32_t old_y=p->y;
        move_player(p,a);
        platform_land(p,a,g->tick,old_y);
        if((keys&FF_PUNCH)&&!(p->previous&FF_PUNCH)&&!p->cooldown) {
            p->punch_ticks=8;p->cooldown=18;g->sounds|=FF_SOUND_PUNCH;
            FF_Player *other=&g->players[1-i];
            int dx=(other->x-p->x)/FF_FP,dy=abs(other->y-p->y)/FF_FP;
            if(!other->respawn&&dx*p->facing>=0&&dx*p->facing<48&&dy<32) {
                damage[1-i]+=12;knock[1-i]=p->facing*22*FF_FP/8;lift[1-i]=-12*FF_FP/8;
            }
        }
        if(p->punch_ticks==8) for(int h=0;h<FF_HAZARDS;++h) {
            FF_Hazard *b=&g->hazards[h];int dx=(b->x-p->x)/FF_FP;
            if(b->life&&dx*p->facing>=0&&dx*p->facing<48&&abs(b->y-p->y+16*FF_FP)<24*FF_FP) {
                b->life=0;blast(g,b->x,b->y);
            }
        }
        if(keys&FF_FIRE) shoot(g,p,i);
        p->previous=input[i];
        if(p->y>(FF_H+32)*FF_FP) damage[i]=1000;
    }
    hazard_tick(g,a,damage);
    for(int i=0;i<FF_SHOTS;++i) {
        FF_Shot *s=&g->shots[i];if(!s->life) continue;
        if(s->kind==FF_ROCKET) rocket_steer(s,g,a);
        if(s->kind==FF_FLAME&&!s->settled) s->vy+=FF_FP/4;
        bool impact=false;int target=-1;
        /* Substeps keep fast shots from tunnelling through a wall or player. */
        int distance=abs(s->vx)>abs(s->vy)?abs(s->vx):abs(s->vy);
        int steps=distance/FF_FP+1;int32_t start_x=s->x,start_y=s->y;
        for(int j=0;j<steps;++j) {
            s->x=start_x+s->vx*(j+1)/steps;s->y=start_y+s->vy*(j+1)/steps;
            int x=s->x/FF_FP,y=s->y/FF_FP;
            int terrain=tile(a,x,y);
            bool surface=terrain==FF_SOLID||(s->kind==FF_FLAME&&s->vy>=0&&terrain==FF_PLATFORM);
            if(surface||x<0||x>=FF_W||y<0||y>=560) {
                if(s->kind==FF_FLAME&&surface&&x>=0&&x<FF_W&&y>=0&&y<=560) {
                    s->x=start_x+s->vx*j/steps;s->y=start_y+s->vy*j/steps;
                    s->vx=s->vy=0;s->settled=1;
                } else impact=true;
                break;
            }
            for(int h=0;h<FF_HAZARDS;++h) {
                FF_Hazard *b=&g->hazards[h];
                if(b->life&&near(s->x,s->y,b->x,b->y,10)) {b->life=0;blast(g,b->x,b->y);impact=true;break;}
            }
            if(impact) break;
            if(s->kind==FF_FLAME) continue;
            FF_Player *p=&g->players[1-s->owner];
            if(!p->respawn&&abs(p->x-s->x)<13*FF_FP&&s->y>=p->y-32*FF_FP&&s->y<p->y) {
                target=1-s->owner;impact=true;break;
            }
        }
        if(target>=0) {
            damage[target]+=s->kind==FF_ICE?6:8;
            if(s->kind==FF_ICE) {knock[target]=(s->vx<0?-6:6)*FF_FP/8;lift[target]=-7*FF_FP/8;}
        }
        if(s->kind==FF_FLAME&&s->life>20&&!impact) for(int k=0;k<2;++k) {
            FF_Player *p=&g->players[k];
            if(p->respawn||p->burn_wait||(!s->settled&&k==s->owner)) continue;
            if(abs(p->x-s->x)<18*FF_FP&&s->y>=p->y-32*FF_FP&&s->y<p->y+4*FF_FP) {
                burning[k]=4;p->burn_wait=6;
            }
        }
        --s->life;
        if(impact||s->life==0) {
            if(s->kind==FF_ROCKET) blast(g,s->x,s->y);
            s->life=0;
        }
    }
    blast_tick(g,damage,knock,lift);
    for(int i=0;i<2;++i) {
        FF_Player *p=&g->players[i];
        if((damage[i]||burning[i])&&(!p->invulnerable||damage[i]>=1000)&&!p->respawn) {
            p->health=clamp(p->health-damage[i]-burning[i],0,100);
            p->vx=clamp(p->vx+knock[i],-100*FF_FP/8,100*FF_FP/8);
            p->vy=clamp(p->vy+lift[i],-100*FF_FP/8,100*FF_FP/8);
            if(lift[i]) p->grounded=0;
            p->invulnerable=damage[i]?10:0;g->sounds|=FF_SOUND_HIT;
            if(!p->health) {--p->lives;p->respawn=75;g->sounds|=FF_SOUND_DEATH;}
        }
    }
    /* Resolve both deaths together so simultaneous final hits draw. */
    if(g->players[0].lives==0||g->players[1].lives==0) {
        g->winner=g->players[0].lives==g->players[1].lives?2:g->players[0].lives?0:1;
        if(g->winner<2) ++g->players[g->winner].score;
        g->round_wait=150;return;
    }
    pickup_spawn(g,a);
    for(int i=0;i<FF_PICKUPS;++i) {
        FF_Pickup *b=&g->pickups[i];if(!b->kind) continue;
        if(!b->active) {
            if(--b->timer<=0) {b->active=1;b->kind=1+(int)(random_word(g)%5);}
            continue;
        }
        for(int j=0;j<2;++j) {
            FF_Player *p=&g->players[j];
            if(!p->respawn&&abs(p->x/FF_FP-b->x)<22&&abs(p->y/FF_FP-16-b->y)<26) {
                pickup(p,b->kind);b->active=0;b->timer=300;if(a->imported) b->kind=0;g->sounds|=FF_SOUND_PICKUP;break;
            }
        }
    }
}
uint32_t ff_game_hash(const FF_Game *g) {
    /* Hash values explicitly; structure padding and host byte order are irrelevant. */
    uint32_t h=2166136261u;
#define HASH(v) do { uint32_t bits=(uint32_t)(v); for(int byte=0;byte<4;++byte) {h^=(bits>>(byte*8))&255u;h*=16777619u;} } while(0)
    HASH(g->pickup_wait);HASH(g->trap_wait);HASH(g->rng);HASH(g->tick);HASH(g->winner);HASH(g->round_wait);HASH(g->sounds);
    for(int i=0;i<2;++i) {const FF_Player *p=&g->players[i];
        HASH(p->x);HASH(p->y);HASH(p->vx);HASH(p->vy);HASH(p->facing);HASH(p->health);HASH(p->lives);HASH(p->score);
        HASH(p->fuel);HASH(p->weapon);HASH(p->ammo);HASH(p->grounded);HASH(p->cooldown);HASH(p->punch_ticks);
        HASH(p->invulnerable);HASH(p->burn_wait);HASH(p->respawn);HASH(p->previous);HASH(p->bounce_wait);
    }
    for(int i=0;i<FF_SHOTS;++i) {const FF_Shot *s=&g->shots[i];
        HASH(s->x);HASH(s->y);HASH(s->vx);HASH(s->vy);HASH(s->kind);HASH(s->owner);HASH(s->life);HASH(s->direction);HASH(s->settled);
    }
    for(int i=0;i<FF_PICKUPS;++i) {const FF_Pickup *p=&g->pickups[i];
        HASH(p->x);HASH(p->y);HASH(p->kind);HASH(p->active);HASH(p->timer);
    }
    for(int i=0;i<FF_HAZARDS;++i) {const FF_Hazard *hazard=&g->hazards[i];
        HASH(hazard->x);HASH(hazard->y);HASH(hazard->vx);HASH(hazard->vy);HASH(hazard->kind);HASH(hazard->life);HASH(hazard->grounded);
    }
    for(int i=0;i<FF_BLASTS;++i) {const FF_Blast *b=&g->blasts[i];
        HASH(b->x);HASH(b->y);HASH(b->life);HASH(b->hit);
    }
#undef HASH
    return h;
}
