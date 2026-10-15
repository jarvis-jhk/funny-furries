#include "game.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
static void tick(FF_Game *g,int a,int b,int n) {uint8_t in[2]={(uint8_t)a,(uint8_t)b};while(n--) ff_game_tick(g,&arena,in);}
static void clean(FF_Game *g) {ff_arena_practice(&arena);arena.bonus_count=0;ff_game_init(g,&arena,1);memset(g->pickups,0,sizeof(g->pickups));for(int i=0;i<2;++i) g->players[i].invulnerable=0;}
static void physics(void) {
    FF_Game g;clean(&g);tick(&g,0,0,100);
    CHECK(g.players[0].grounded);CHECK(g.players[0].y==560*FF_FP);
    int x=g.players[0].x;tick(&g,FF_RIGHT,0,20);CHECK(g.players[0].x>x+40*FF_FP);
    tick(&g,FF_JUMP,0,1);CHECK(g.players[0].vy<0);int apex=g.players[0].y;
    tick(&g,FF_JUMP,0,20);CHECK(g.players[0].y<apex);CHECK(g.players[0].y>430*FF_FP);
    tick(&g,0,0,100);CHECK(g.players[0].grounded);
    tick(&g,FF_LEFT,0,500);CHECK(g.players[0].x>=27*FF_FP);CHECK(g.players[0].x<30*FF_FP);
    /* A jump passes through a one-way platform and lands on its top. */
    g.players[0].x=100*FF_FP;g.players[0].y=460*FF_FP;g.players[0].grounded=1;g.players[0].vx=0;
    tick(&g,FF_JUMP,0,1);tick(&g,0,0,60);CHECK(g.players[0].y==432*FF_FP);CHECK(g.players[0].grounded);
    /* Full solids stop upward motion as well as downward motion. */
    arena.tiles[25][6]=FF_SOLID;g.players[0].x=104*FF_FP;g.players[0].y=460*FF_FP;g.players[0].grounded=1;
    tick(&g,FF_JUMP,0,1);CHECK(g.players[0].y>=448*FF_FP);tick(&g,0,0,3);CHECK(g.players[0].vy>=0);
}
static void melee_round(void) {
    FF_Game g;clean(&g);
    g.players[0].x=300*FF_FP;g.players[1].x=330*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].health=g.players[1].health=12;
    tick(&g,FF_PUNCH,FF_PUNCH,1);
    CHECK(g.players[0].health==0);CHECK(g.players[1].health==0);CHECK(g.players[0].lives==2);CHECK(g.players[1].lives==2);
    tick(&g,0,0,75);CHECK(g.players[0].health==100);CHECK(g.players[0].invulnerable>0);
    g.players[1].health=1;g.players[1].lives=1;g.players[1].invulnerable=0;
    g.players[0].invulnerable=0;g.players[0].x=300*FF_FP;g.players[1].x=330*FF_FP;
    g.players[0].y=g.players[1].y=560*FF_FP;g.players[0].facing=1;
    tick(&g,FF_PUNCH,0,1);CHECK(g.winner==0);CHECK(g.players[0].score==1);
    tick(&g,0,0,150);CHECK(g.winner==-1);CHECK(g.players[1].lives==3);CHECK(g.players[0].score==1);
    /* Holding punch does not produce repeat punches. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=330*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    tick(&g,FF_PUNCH,0,25);CHECK(g.players[1].health==88);
}
static void weapons(void) {
    FF_Game g;clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=360*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    tick(&g,FF_FIRE,0,8);CHECK(g.players[1].health==94);CHECK(g.players[1].frozen>0);CHECK(g.players[0].ammo==0);CHECK(g.players[0].weapon==FF_FISTS);
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=360*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_ROCKET;g.players[0].ammo=1;tick(&g,FF_FIRE,0,12);CHECK(g.players[1].health==84);
    /* Frame-3 shooting rows set eight ticks for ice/flame and fifty for rockets. */
    clean(&g);g.players[0].weapon=FF_ROCKET;g.players[0].ammo=3;
    tick(&g,FF_FIRE,0,50);CHECK(g.players[0].ammo==2);
    tick(&g,FF_FIRE,0,1);CHECK(g.players[0].ammo==1);
    clean(&g);g.players[0].weapon=FF_ICE;g.players[0].ammo=3;
    tick(&g,FF_FIRE,0,8);CHECK(g.players[0].ammo==2);
    tick(&g,FF_FIRE,0,1);CHECK(g.players[0].ammo==1);
    /* A wall absorbs a fast projectile before it reaches the target. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=370*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    arena.tiles[33][21]=FF_SOLID;arena.tiles[34][21]=FF_SOLID;g.players[0].weapon=FF_ICE;g.players[0].ammo=5;
    tick(&g,FF_FIRE,0,40);CHECK(g.players[1].health==100);
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=340*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_FLAME;g.players[0].ammo=15;tick(&g,FF_FIRE,0,25);CHECK(g.players[1].health<100);CHECK(g.players[0].ammo<15);
}
static void homing_rockets(void) {
    FF_Game g;clean(&g);memset(arena.tiles,0,sizeof(arena.tiles));
    FF_Player *p=&g.players[0],*target=&g.players[1];
    p->x=200*FF_FP;p->y=400*FF_FP;target->x=600*FF_FP;target->y=200*FF_FP;
    p->weapon=FF_ROCKET;p->ammo=1;tick(&g,FF_FIRE,0,1);
    CHECK(g.shots[0].life&&g.shots[0].vy<0&&g.shots[0].vx>0);
    int old_y=g.shots[0].y;tick(&g,0,0,5);CHECK(g.shots[0].y<old_y);
    /* A dead/respawning opponent is never a new homing target. */
    target->respawn=60;int direction=g.shots[0].direction;
    tick(&g,0,0,1);CHECK(g.shots[0].direction==direction);
    /* Crossing a wind volume turns a rocket even with no live target. */
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_WIND_UP,0,0,800,560,-1};
    tick(&g,0,0,1);CHECK(g.shots[0].direction==direction+1);
    /* A steep shot cannot tunnel through a one-pixel ceiling. */
    clean(&g);arena.imported=true;
    memset(&arena.mask[200][80],FF_SOLID,100);
    g.players[0].x=600*FF_FP;g.players[1].respawn=60;
    g.shots[0]=(FF_Shot){120*FF_FP,206*FF_FP,0,-57*FF_FP/8,FF_ROCKET,0,100,8};
    tick(&g,0,0,1);CHECK(!g.shots[0].life&&g.blasts[0].life);
    CHECK(g.blasts[0].y>=200*FF_FP&&g.blasts[0].y<201*FF_FP);
    /* Substeps preserve the exact displacement of a fractional-speed shot. */
    clean(&g);g.players[1].respawn=60;
    g.shots[0]=(FF_Shot){300*FF_FP,100*FF_FP,100*FF_FP/8,0,FF_ICE,0,100,0};
    tick(&g,0,0,1);CHECK(g.shots[0].x==300*FF_FP+100*FF_FP/8);
    FF_Game replay=g;replay.shots[0].direction=1;CHECK(ff_game_hash(&g)!=ff_game_hash(&replay));
}
static void bonuses(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];p->y=560*FF_FP;p->health=80;
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_HEALTH,1,0};tick(&g,0,0,1);CHECK(p->health==100);CHECK(!g.pickups[0].active);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ICE,1,0};tick(&g,0,0,1);CHECK(p->weapon==FF_ICE&&p->ammo==25);
    g.pickups[0].active=1;tick(&g,0,0,1);CHECK(p->ammo==50);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ROCKET,1,0};tick(&g,0,0,1);CHECK(p->weapon==FF_ROCKET&&p->ammo==8);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_FUEL,1,0};tick(&g,0,0,1);CHECK(p->fuel==150);
    int y=p->y;tick(&g,FF_FLY,0,30);CHECK(p->y<y);CHECK(p->fuel==120);
}
static void arena_devices(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];
    p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_WATER,80,200,48,16,0};
    tick(&g,0,0,30);CHECK(p->vy<=2*FF_FP);
    int y=p->y;tick(&g,FF_JUMP,0,1);CHECK(p->vy<0);tick(&g,FF_JUMP,0,20);CHECK(p->y<y);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_FAN_UP,80,350,48,16,0};
    tick(&g,0,0,10);CHECK(p->vy<0);CHECK(p->y<300*FF_FP);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_BOUNCE_UP,80,295,48,16,0};
    tick(&g,0,0,1);CHECK(p->vy==-9*FF_FP);CHECK(p->bounce_wait>0);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->grounded=1;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_MOVING_PLATFORM,80,300,48,16,0};
    tick(&g,0,0,10);CHECK(p->x==120*FF_FP);CHECK(p->y==300*FF_FP);CHECK(p->grounded);
    tick(&g,FF_JUMP,0,1);CHECK(p->vy<0);CHECK(p->y<300*FF_FP);
    CHECK(ff_device_position(&arena,0,0).x==80);
    CHECK(ff_device_position(&arena,0,64).x==208);
    CHECK(ff_device_position(&arena,0,128).x==80);
}
static void marker_collision_and_paths(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];
    memset(arena.tiles,0,sizeof(arena.tiles));arena.imported=true;
    memset(&arena.mask[300][80],FF_PLATFORM,100);
    p->x=120*FF_FP;p->y=330*FF_FP;p->grounded=1;
    tick(&g,FF_JUMP,0,1);tick(&g,0,0,70);
    CHECK(p->y==300*FF_FP&&p->grounded);
    /* Walking off the hidden marker resumes falling. */
    tick(&g,FF_RIGHT,0,50);CHECK(p->y>300*FF_FP);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->grounded=1;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_MOVING_PLATFORM,80,300,48,16,0};
    arena.paths[0]=(FF_Path){64,144,1,-1};
    CHECK(ff_device_position(&arena,0,16).x==64);
    CHECK(ff_device_position(&arena,0,96).x==144);
    CHECK(ff_device_position(&arena,0,160).x==80);
    tick(&g,0,0,160);CHECK(p->x==100*FF_FP&&p->y==300*FF_FP&&p->grounded);
}
static void hazards_and_blasts(void) {
    FF_Game g;clean(&g);
    /* Contact and the resulting explosion are separate eight-point hits. */
    for(int i=0;i<2;++i) {g.players[i].x=300*FF_FP;g.players[i].y=560*FF_FP;}
    g.hazards[0]=(FF_Hazard){300*FF_FP,544*FF_FP,0,0,FF_BOMB_FLY,200,0};
    tick(&g,0,0,1);CHECK(!g.hazards[0].life);
    CHECK(g.players[0].health==84&&g.players[1].health==84);
    CHECK(g.sounds&FF_SOUND_BLAST);
    tick(&g,0,0,25);CHECK(g.players[0].health==84&&g.players[1].health==84);
    /* Each player can enter a still-live explosion once, including its owner. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.players[1].x=430*FF_FP;g.players[1].y=560*FF_FP;
    g.blasts[0]=(FF_Blast){300*FF_FP,544*FF_FP,20,0};tick(&g,0,0,1);
    CHECK(g.players[0].health==92&&g.players[1].health==100);
    g.players[1].x=320*FF_FP;tick(&g,0,0,1);CHECK(g.players[1].health==92);
    tick(&g,0,0,17);CHECK(g.players[0].health==92&&g.players[1].health==92);
    /* Reverse slot order must still propagate an entire chain. */
    clean(&g);g.players[0].invulnerable=g.players[1].invulnerable=100;
    for(int i=0;i<4;++i) g.hazards[3-i]=(FF_Hazard){(300+35*i)*FF_FP,200*FF_FP,0,0,FF_BOMB_FLY,200,0};
    g.blasts[0]=(FF_Blast){280*FF_FP,200*FF_FP,20,0};tick(&g,0,0,1);
    for(int i=0;i<4;++i) CHECK(!g.hazards[i].life);
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    g.hazards[0]=(FF_Hazard){345*FF_FP,542*FF_FP,0,0,FF_BOMB_FLY,200,0};
    tick(&g,FF_FIRE,0,8);CHECK(!g.hazards[0].life);
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.hazards[0]=(FF_Hazard){340*FF_FP,544*FF_FP,0,0,FF_BOMB_FLY,200,0};
    tick(&g,FF_PUNCH,0,1);CHECK(!g.hazards[0].life);
    /* A walking bomb turns before stepping off a ledge. */
    clean(&g);arena.imported=true;memset(arena.tiles,0,sizeof(arena.tiles));
    memset(&arena.mask[300][80],FF_PLATFORM,100);
    g.hazards[0]=(FF_Hazard){173*FF_FP,299*FF_FP,FF_FP,0,FF_BOMB_WALK,200,1};
    tick(&g,0,0,1);CHECK(g.hazards[0].vx<0);
    /* Falling bombs bounce from one-way surfaces but detonate on solids. */
    g.hazards[0]=(FF_Hazard){120*FF_FP,299*FF_FP,0,FF_FP,FF_BOMB,200,0};
    tick(&g,0,0,1);CHECK(g.hazards[0].life&&g.hazards[0].vy<0);
    memset(&arena.mask[300][80],FF_SOLID,100);
    g.hazards[0]=(FF_Hazard){120*FF_FP,299*FF_FP,0,FF_FP,FF_BOMB,200,0};
    tick(&g,0,0,1);CHECK(!g.hazards[0].life);
    /* Scheduled hazards use the arena's actual bonus points and seeded RNG. */
    clean(&g);arena.bonus_count=1;arena.bonuses[0]=(FF_Point){400,100};
    g.trap_wait=1;FF_Game replay=g;
    tick(&g,0,0,1);tick(&replay,0,0,1);CHECK(ff_game_hash(&g)==ff_game_hash(&replay));
    CHECK(g.hazards[0].life&&g.hazards[0].y>=100*FF_FP&&g.trap_wait>=200);
    CHECK(g.hazards[0].kind>=FF_BOMB&&g.hazards[0].kind<=FF_BOMB_FLY);
    tick(&g,0,0,1800);tick(&replay,0,0,1800);CHECK(ff_game_hash(&g)==ff_game_hash(&replay));
}
static void reference_jump(void) {
    FF_Game g;clean(&g);g.players[0].x=100*FF_FP;g.players[0].y=560*FF_FP;g.players[0].grounded=1;
    int top=g.players[0].y;tick(&g,FF_JUMP,0,1);
    for(int i=0;i<44;++i) {if(g.players[0].y<top) top=g.players[0].y;tick(&g,0,0,1);}
    CHECK(560*FF_FP-top>=63*FF_FP&&560*FF_FP-top<=64*FF_FP);
    CHECK(g.players[0].grounded);
    tick(&g,FF_RIGHT,0,20);CHECK(g.players[0].vx==25*FF_FP/8);
}
static void wind_and_bonus_regions(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];
    p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=2;
    arena.devices[0]=(FF_Device){FF_FAN_UP,80,350,48,16,0};
    arena.devices[1]=(FF_Device){FF_WIND_UP,80,200,32,100,-1};
    tick(&g,0,0,1);CHECK(p->vy<0);
    p->x=125*FF_FP;p->y=380*FF_FP;p->vy=0;
    tick(&g,0,0,1);CHECK(p->vy==FF_FP/4); // The visible fan does not add a second region.
    p->x=100*FF_FP;p->y=280*FF_FP;p->vx=p->vy=0;
    arena.devices[1].kind=FF_WIND_LEFT;tick(&g,0,0,1);CHECK(p->vx==-5*FF_FP/8);
    clean(&g);arena.imported=true;arena.bonus_count=1;arena.bonuses[0]=(FF_Point){400,100};
    ff_game_init(&g,&arena,1);int active=0;
    for(int i=0;i<FF_PICKUPS;++i) active+=g.pickups[i].active;
    CHECK(!active&&g.pickup_wait>=300&&g.pickup_wait<600);
    g.pickup_wait=1;g.trap_wait=10000;tick(&g,0,0,1);
    CHECK(g.pickups[0].active&&g.pickups[0].x==400&&g.pickups[0].y==100);
    CHECK(g.pickup_wait>=100&&g.pickup_wait<1000);
    p=&g.players[0];p->x=400*FF_FP;p->y=116*FF_FP;p->vy=0;
    tick(&g,0,0,1);CHECK(!g.pickups[0].active&&!g.pickups[0].kind);
    /* Consumed imported bonuses wait for the global timer, not a per-item respawn. */
    g.pickup_wait=500;tick(&g,0,0,301);CHECK(!g.pickups[0].kind);
}
static void determinism(void) {
    FF_Game a,b;clean(&a);b=a;
    uint32_t r=17;
    for(int i=0;i<10000;++i) {
        r=r*1664525u+1013904223u;uint8_t keys[2]={(uint8_t)(r&63),(uint8_t)((r>>8)&63)};
        ff_game_tick(&a,&arena,keys);ff_game_tick(&b,&arena,keys);
        CHECK(ff_game_hash(&a)==ff_game_hash(&b));
        for(int k=0;k<2;++k) {CHECK(a.players[k].ammo>=0);CHECK(a.players[k].health>=0&&a.players[k].health<=100);}
    }
    /* The checksum includes state that will change future input transitions. */
    b.players[0].previous^=FF_JUMP;CHECK(ff_game_hash(&a)!=ff_game_hash(&b));
    printf("replay=%08x\n",ff_game_hash(&a));
}
int main(void) {physics();melee_round();weapons();homing_rockets();bonuses();arena_devices();marker_collision_and_paths();hazards_and_blasts();reference_jump();wind_and_bonus_regions();determinism();printf("%u game checks passed\n",checks);return 0;}
