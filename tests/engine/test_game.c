#include "game.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
static void tick(FF_Game *g,int a,int b,int n) {uint8_t in[2]={(uint8_t)a,(uint8_t)b};while(n--) ff_game_tick(g,&arena,in);}
static void clean(FF_Game *g) {ff_arena_practice(&arena);ff_game_init(g,&arena,1);memset(g->pickups,0,sizeof(g->pickups));for(int i=0;i<2;++i) g->players[i].invulnerable=0;}
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
    tick(&g,FF_JUMP,0,1);CHECK(g.players[0].y>=448*FF_FP);tick(&g,0,0,2);CHECK(g.players[0].vy>=0);
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
    /* A wall absorbs a fast projectile before it reaches the target. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=370*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    arena.tiles[33][21]=FF_SOLID;arena.tiles[34][21]=FF_SOLID;g.players[0].weapon=FF_ICE;g.players[0].ammo=5;
    tick(&g,FF_FIRE,0,40);CHECK(g.players[1].health==100);
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=340*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_FLAME;g.players[0].ammo=15;tick(&g,FF_FIRE,0,25);CHECK(g.players[1].health<100);CHECK(g.players[0].ammo<15);
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
    CHECK(ff_device_position(&arena.devices[0],0).x==80);
    CHECK(ff_device_position(&arena.devices[0],64).x==208);
    CHECK(ff_device_position(&arena.devices[0],128).x==80);
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
int main(void) {physics();melee_round();weapons();bonuses();arena_devices();determinism();printf("%u game checks passed\n",checks);return 0;}
