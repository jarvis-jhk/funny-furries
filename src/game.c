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
    if(x-11<0||x+11>=FF_W||y-32<0) return true;
    if(a->imported) {
        for(int yy=y-32;yy<y&&yy<FF_H;++yy)
            for(int xx=x-11;xx<=x+11;++xx) if(a->mask[yy][xx]==FF_SOLID) return true;
        return false;
    }
    for(int row=(y-32)/FF_TILE;row<=(y-1)/FF_TILE;++row)
        for(int col=(x-11)/FF_TILE;col<=(x+11)/FF_TILE;++col)
            if(tile(a,col*FF_TILE,row*FF_TILE)==FF_SOLID) return true;
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
            int left=tile(a,x-10,yy-1),right=tile(a,x+10,yy-1);
            /* One-way tops catch only a crossing from above. */
            if(a->imported) {
                for(int xx=x-10;xx<=x+10;++xx)
                    if(tile(a,xx,yy-1)==FF_PLATFORM&&tile(a,xx,yy-2)!=FF_PLATFORM) hit=true;
            } else if((yy-1)%FF_TILE==0&&(left==FF_PLATFORM||right==FF_PLATFORM)) hit=true;
        }
        if(hit) {next=(yy-step)*FF_FP;p->vy=0;p->grounded=step>0;break;}
    }
    p->y=next;
    if(!p->grounded&&p->vy>=0) {
        y=floor_pixel(p->y);
        p->grounded=blocked(a,x,y+1)||
            ((a->imported||y%FF_TILE==0)&&(tile(a,x-10,y)==FF_PLATFORM||tile(a,x+10,y)==FF_PLATFORM));
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
static void device_forces(FF_Player *p,const FF_Arena *a) {
    int x=p->x/FF_FP,y=p->y/FF_FP-16;
    if(p->bounce_wait) --p->bounce_wait;
    bool wind_volumes=false;
    for(int i=0;i<a->device_count;++i) if(a->devices[i].kind>=FF_WIND_LEFT) wind_volumes=true;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(!wind_volumes&&d->kind==FF_FAN_UP&&x>=d->x&&x<d->x+d->w&&y>d->y-110&&y<d->y+12) p->vy=clamp(p->vy-FF_FP/2,-5*FF_FP,8*FF_FP);
        if(!wind_volumes&&d->kind==FF_FAN_LEFT&&y>=d->y&&y<d->y+d->h&&x>d->x-110&&x<d->x+12) p->vx=clamp(p->vx-FF_FP/2,-6*FF_FP,6*FF_FP);
        if(!wind_volumes&&d->kind==FF_FAN_RIGHT&&y>=d->y&&y<d->y+d->h&&x>d->x-12&&x<d->x+110) p->vx=clamp(p->vx+FF_FP/2,-6*FF_FP,6*FF_FP);
        if(d->kind>=FF_WIND_LEFT&&x+11>=d->x&&x-11<d->x+d->w&&y+16>=d->y&&y-16<d->y+d->h) {
            if(d->kind==FF_WIND_UP) p->vy=clamp(p->vy-5*FF_FP/8,-5*FF_FP,8*FF_FP);
            else p->vx=clamp(p->vx+(d->kind==FF_WIND_LEFT?-5:5)*FF_FP/8,-6*FF_FP,6*FF_FP);
        }
        if(p->bounce_wait||d->kind<FF_BOUNCE_UP||d->kind>FF_BOUNCE_RIGHT) continue;
        if(x+12<d->x||x-12>=d->x+d->w||y+16<d->y||y-16>=d->y+d->h) continue;
        if(d->kind==FF_BOUNCE_UP) p->vy=-9*FF_FP;
        if(d->kind==FF_BOUNCE_DOWN) p->vy=8*FF_FP;
        if(d->kind==FF_BOUNCE_LEFT) p->vx=-8*FF_FP;
        if(d->kind==FF_BOUNCE_RIGHT) p->vx=8*FF_FP;
        p->grounded=0;p->bounce_wait=15;
    }
}
static void platform_carry(FF_Player *p,const FF_Arena *a,uint32_t tick) {
    if(!p->grounded) return;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];if(d->kind!=FF_MOVING_PLATFORM) continue;
        FF_Point old=ff_device_position(a,i,tick-1),now=ff_device_position(a,i,tick);
        int x=p->x/FF_FP,y=p->y/FF_FP;
        if(y==old.y&&x+10>=old.x&&x-10<old.x+d->w) {
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
        if(old_y<=now.y*FF_FP&&p->y>=now.y*FF_FP&&x+10>=now.x&&x-10<now.x+d->w) {
            p->y=now.y*FF_FP;p->vy=0;p->grounded=1;
        }
    }
}
static void shoot(FF_Game *g,FF_Player *p,int owner) {
    if(p->weapon==FF_FISTS||p->ammo<=0||p->cooldown) return;
    for(int i=0;i<FF_SHOTS;++i) if(!g->shots[i].life) {
        int kind=p->weapon;
        g->shots[i]=(FF_Shot){p->x+p->facing*16*FF_FP,p->y-18*FF_FP,
            p->facing*(kind==FF_ICE?100:kind==FF_ROCKET?57:40)*FF_FP/8,0,kind,owner,kind==FF_FLAME?12:100};
        --p->ammo;p->cooldown=kind==FF_ROCKET?50:8;
        g->sounds|=kind==FF_ICE?FF_SOUND_ICE:kind==FF_ROCKET?FF_SOUND_ROCKET:FF_SOUND_FLAME;
        if(!p->ammo) p->weapon=FF_FISTS;
        return;
    }
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
static void blast_tick(FF_Game *g,int damage[2],int knock[2]) {
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
                b->hit|=1u<<k;damage[k]+=8;knock[k]=(p->x<b->x?-3:3)*FF_FP;
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
    int damage[2]={0}, freeze[2]={0}, knock[2]={0};
    for(int i=0;i<2;++i) {
        FF_Player *p=&g->players[i];uint8_t keys=input[i];
        if(p->respawn) {
            if(--p->respawn==0) reset_player(p,spawn(g,a,i),i);
            p->previous=keys;continue;
        }
        if(p->invulnerable) --p->invulnerable;
        if(p->cooldown) --p->cooldown;
        if(p->punch_ticks) --p->punch_ticks;
        if(p->frozen) {--p->frozen;keys=0;}
        if(p->swim_wait) --p->swim_wait;
        bool wet=underwater(p,a);
        platform_carry(p,a,g->tick);
        int horizontal=!!(keys&FF_RIGHT)-!!(keys&FF_LEFT);
        if(horizontal) {p->vx=clamp(p->vx+horizontal*FF_FP/2,-25*FF_FP/8,25*FF_FP/8);p->facing=horizontal;}
        else if(p->vx>0) p->vx=clamp(p->vx-FF_FP/8,0,25*FF_FP/8);
        else if(p->vx<0) p->vx=clamp(p->vx+FF_FP/8,-25*FF_FP/8,0);
        p->vy=clamp(p->vy+(wet?FF_FP/10:FF_FP/4),-9*FF_FP,wet?2*FF_FP:8*FF_FP);
        if((keys&FF_JUMP)&&!(p->previous&FF_JUMP)&&p->grounded) {p->vy=-44*FF_FP/8;p->grounded=0;}
        if(wet) {
            p->vx=clamp(p->vx,-2*FF_FP,2*FF_FP);
            if((keys&FF_JUMP)&&!p->swim_wait) {p->vy=-3*FF_FP;p->swim_wait=15;}
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
                damage[1-i]+=12;knock[1-i]=p->facing*3*FF_FP;
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
        bool impact=false;int target=-1;
        /* Substeps keep fast shots from tunnelling through a wall or player. */
        int steps=abs(s->vx)/FF_FP;if(steps<1) steps=1;
        for(int j=0;j<steps;++j) {
            s->x+=s->vx/steps;s->y+=s->vy/steps;
            int x=s->x/FF_FP,y=s->y/FF_FP;
            if(tile(a,x,y)==FF_SOLID||x<0||x>=FF_W||y>=FF_H) {impact=true;break;}
            for(int h=0;h<FF_HAZARDS;++h) {
                FF_Hazard *b=&g->hazards[h];
                if(b->life&&near(s->x,s->y,b->x,b->y,10)) {b->life=0;blast(g,b->x,b->y);impact=true;break;}
            }
            if(impact) break;
            FF_Player *p=&g->players[1-s->owner];
            if(!p->respawn&&abs(p->x-s->x)<13*FF_FP&&s->y>=p->y-32*FF_FP&&s->y<p->y) {
                target=1-s->owner;impact=true;break;
            }
        }
        if(target>=0) {
            damage[target]+=s->kind==FF_ICE?6:s->kind==FF_ROCKET?8:2;
            freeze[target]=s->kind==FF_ICE?15:0;knock[target]=s->vx/3;
        }
        --s->life;
        if(impact||s->life==0) {
            if(s->kind==FF_ROCKET) blast(g,s->x,s->y);
            s->life=0;
        }
    }
    blast_tick(g,damage,knock);
    for(int i=0;i<2;++i) {
        FF_Player *p=&g->players[i];
        if(damage[i]&&(!p->invulnerable||damage[i]>=1000)&&!p->respawn) {
            p->health=clamp(p->health-damage[i],0,100);p->vx=knock[i];p->frozen=freeze[i];
            p->invulnerable=damage[i]<=2?0:10;g->sounds|=FF_SOUND_HIT;
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
        HASH(p->invulnerable);HASH(p->frozen);HASH(p->respawn);HASH(p->previous);HASH(p->swim_wait);HASH(p->bounce_wait);
    }
    for(int i=0;i<FF_SHOTS;++i) {const FF_Shot *s=&g->shots[i];
        HASH(s->x);HASH(s->y);HASH(s->vx);HASH(s->vy);HASH(s->kind);HASH(s->owner);HASH(s->life);
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
