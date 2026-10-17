#include "game.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
static void tick(FF_Game *g,int a,int b,int n) {uint8_t in[FF_PLAYERS]={(uint8_t)a,(uint8_t)b};while(n--) ff_game_tick(g,&arena,in);}
static void restart(FF_Game *g) {ff_game_init(g,&arena,1);memset(g->pickups,0,sizeof(g->pickups));for(int i=0;i<2;++i) g->players[i].invulnerable=0;}
static void clean(FF_Game *g) {ff_arena_practice(&arena);arena.bonus_count=0;restart(g);}
static void place(FF_Game *g,int i,int x) {FF_Player *p=&g->players[i];p->x=x*FF_FP;p->y=560*FF_FP;p->vx=p->vy=0;p->invulnerable=0;p->grounded=1;}
/* Where platform 0 is after n ticks of a fresh game on the current arena. */
static int platform_after(int n) {static FF_Game g;restart(&g);tick(&g,0,0,n);return ff_device_position(&arena,&g,0).x;}
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
    /* Holding punch repeats only after the original 25-tick hand cooldown. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=330*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    tick(&g,FF_PUNCH,0,25);CHECK(g.players[1].health==88);
    g.players[1].x=330*FF_FP;g.players[1].y=560*FF_FP;g.players[1].vx=g.players[1].vy=0;
    tick(&g,FF_PUNCH,0,1);CHECK(g.players[1].health==76);
}
static void weapons(void) {
    FF_Game g;clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=360*FF_FP;g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    tick(&g,FF_FIRE,0,8);CHECK(g.players[1].health==94);CHECK(g.players[0].ammo==0);CHECK(g.players[0].weapon==FF_FISTS);
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
    g.shots[0]=(FF_Shot){120*FF_FP,206*FF_FP,0,-57*FF_FP/8,FF_ROCKET,0,100,8,0,0};
    tick(&g,0,0,1);CHECK(!g.shots[0].life&&g.blasts[0].life);
    CHECK(g.blasts[0].y>=200*FF_FP&&g.blasts[0].y<201*FF_FP);
    /* A missile that turns back can hit its shooter, including direct damage. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;g.players[1].respawn=60;
    g.shots[0]=(FF_Shot){325*FF_FP,542*FF_FP,-57*FF_FP/8,0,FF_ROCKET,0,100,16,0,0};
    tick(&g,0,0,2);CHECK(g.players[0].health==84&&!g.shots[0].life);
    /* Substeps preserve the exact displacement of a fractional-speed shot. */
    clean(&g);g.players[1].respawn=60;
    g.shots[0]=(FF_Shot){300*FF_FP,100*FF_FP,100*FF_FP/8,0,FF_ICE,0,100,0,0,0};
    tick(&g,0,0,1);CHECK(g.shots[0].x==300*FF_FP+100*FF_FP/8);
    FF_Game replay=g;replay.shots[0].direction=1;CHECK(ff_game_hash(&g)!=ff_game_hash(&replay));
}
static void persistent_flame_and_impulses(void) {
    FF_Game g;clean(&g);
    for(int i=0;i<2;++i) {g.players[i].x=(300+80*i)*FF_FP;g.players[i].y=560*FF_FP;}
    g.players[0].weapon=FF_FLAME;g.players[0].ammo=1;
    tick(&g,FF_FIRE,0,25);
    CHECK(g.shots[0].life>200&&g.shots[0].settled);
    CHECK(g.players[1].health<=88&&g.players[0].health==100);
    /* A fire patch hurts its owner too; overlapping patches share a six-tick gate. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.shots[0]=(FF_Shot){300*FF_FP,559*FF_FP,0,0,FF_FLAME,0,270,0,1,0};
    g.shots[1]=g.shots[0];tick(&g,0,0,1);CHECK(g.players[0].health==96);
    tick(&g,0,0,5);CHECK(g.players[0].health==96);
    tick(&g,0,0,1);CHECK(g.players[0].health==92);
    g.shots[0].life=g.shots[1].life=20;tick(&g,0,0,25);
    CHECK(!g.shots[0].life&&g.players[0].health==92);
    /* Ice knocks back and up, with controls available on the very next tick. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[1].x=340*FF_FP;
    g.players[0].y=g.players[1].y=560*FF_FP;
    g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    tick(&g,FF_FIRE,0,1);CHECK(g.players[1].health==94&&g.players[1].vy<0);
    tick(&g,0,FF_LEFT,1);CHECK(g.players[1].facing==-1);
    /* External impulses decay instead of vanishing at the run speed cap. */
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=400*FF_FP;
    g.players[0].vx=10*FF_FP;tick(&g,FF_RIGHT,0,1);CHECK(g.players[0].vx>9*FF_FP);
}
static void bonuses(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];p->y=560*FF_FP;p->health=80;
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_HEALTH,1,0};tick(&g,0,0,1);CHECK(p->health==100);CHECK(!g.pickups[0].active);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ICE,1,0};tick(&g,0,0,1);CHECK(p->weapon==FF_ICE&&p->ammo==25);
    g.pickups[0].active=1;tick(&g,0,0,1);CHECK(p->ammo==50);
    /* Like the original, a bonus that would change nothing stays: full ice ammo, another
     * weapon in hand, full health, a full tank. */
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ICE,1,0};tick(&g,0,0,1);CHECK(p->ammo==50&&g.pickups[0].active);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ROCKET,1,0};tick(&g,0,0,1);CHECK(p->weapon==FF_ICE&&g.pickups[0].active);
    CHECK(p->health==100);g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_HEALTH,1,0};tick(&g,0,0,1);CHECK(g.pickups[0].active);
    p->health=99;tick(&g,0,0,1);CHECK(p->health==100&&!g.pickups[0].active);
    p->weapon=FF_FISTS;p->ammo=0;
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_ROCKET,1,0};tick(&g,0,0,1);CHECK(p->weapon==FF_ROCKET&&p->ammo==8);
    g.pickups[0]=(FF_Pickup){p->x/FF_FP,544,FF_FUEL,1,0};tick(&g,0,0,1);CHECK(p->fuel==150);
    int y=p->y;tick(&g,FF_FLY,0,30);CHECK(p->y<y);CHECK(p->fuel==120);
    p->fuel=300;g.pickups[0]=(FF_Pickup){p->x/FF_FP,p->y/FF_FP-16,FF_FUEL,1,0};tick(&g,0,0,1);CHECK(g.pickups[0].active&&p->fuel==300);
}
static void arena_devices(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];
    p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_WATER,80,200,48,16,0};
    tick(&g,0,0,30);CHECK(p->vy<=20*FF_FP/8);
    int y=p->y;tick(&g,FF_JUMP,0,45);CHECK(p->vy<0);CHECK(p->y<y);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_FAN_UP,80,350,48,16,0};
    tick(&g,0,0,10);CHECK(p->vy<0);CHECK(p->y<300*FF_FP);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_BOUNCE_UP,80,295,48,16,0};
    tick(&g,0,0,1);CHECK(p->vy==-22*FF_FP/8);CHECK(p->bounce_wait>0);
    clean(&g);arena.device_count=1;arena.devices[0]=(FF_Device){FF_MOVING_PLATFORM,80,300,48,16,0};
    restart(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->grounded=1;
    tick(&g,0,0,10);CHECK(p->x==120*FF_FP);CHECK(p->y==300*FF_FP);CHECK(p->grounded);
    tick(&g,FF_JUMP,0,1);CHECK(p->vy<0);CHECK(p->y<300*FF_FP);
    CHECK(platform_after(0)==80);
    CHECK(platform_after(64)==208);
    CHECK(platform_after(128)==80);
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
    clean(&g);arena.device_count=1;arena.devices[0]=(FF_Device){FF_MOVING_PLATFORM,80,300,48,16,0};
    arena.paths[0]=(FF_Path){64,144,1,-1};
    CHECK(platform_after(16)==64);
    CHECK(platform_after(96)==144);
    CHECK(platform_after(160)==80);
    restart(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->grounded=1;
    tick(&g,0,0,160);CHECK(p->x==100*FF_FP&&p->y==300*FF_FP&&p->grounded);
}
static void sensor_body_and_directional_bounces(void) {
    FF_Game g;clean(&g);arena.imported=true;
    FF_Player *p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;
    /* The hat's transparent corner is not a solid rectangular collision body. */
    arena.mask[274][110]=FF_SOLID;arena.mask[300][100]=FF_PLATFORM;
    tick(&g,FF_RIGHT,0,2);CHECK(p->x>101*FF_FP);
    CHECK(p->grounded&&p->y==300*FF_FP); // Even a one-pixel top supports the feet.
    /* A solid pixel inside the narrow head does stop upward travel. */
    p->vx=0;p->x=100*FF_FP;p->y=300*FF_FP;p->grounded=1;
    arena.mask[273][100]=FF_SOLID;tick(&g,FF_JUMP,0,1);CHECK(p->vy==0&&p->y==300*FF_FP);
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->vx=FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_BOUNCE_LEFT,100,280,8,32,0};
    tick(&g,FF_RIGHT,0,1);CHECK(p->vx==-100*FF_FP/8);
    tick(&g,FF_LEFT,0,1);CHECK(p->vx<-12*FF_FP); // Held input preserves the impulse.
    CHECK(p->vx<0); // Moving away cannot retrigger the spring.
    /* Upward spring energy depends on incoming fall speed, plus the stored 20. */
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->vy=4*FF_FP;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_BOUNCE_UP,80,295,48,16,0};
    tick(&g,0,0,1);CHECK(p->vy==-54*FF_FP/8);
    /* Swimming accelerates while held, rather than injecting periodic jumps. */
    clean(&g);p=&g.players[0];p->x=100*FF_FP;p->y=300*FF_FP;p->vy=0;
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_WATER,80,200,48,16,0};
    tick(&g,FF_JUMP,0,1);CHECK(p->vy==-FF_FP/8);
    tick(&g,FF_JUMP,0,9);CHECK(p->vy==-10*FF_FP/8);
    tick(&g,0,0,1);CHECK(p->vy==-9*FF_FP/8);
}
static void hazards_and_blasts(void) {
    FF_Game g;clean(&g);
    /* Contact and the resulting explosion are separate eight-point hits. */
    for(int i=0;i<2;++i) {g.players[i].x=300*FF_FP;g.players[i].y=560*FF_FP;}
    g.hazards[0]=(FF_Hazard){300*FF_FP,544*FF_FP,0,0,FF_BOMB_FLY,1,0,0};
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
    for(int i=0;i<4;++i) g.hazards[3-i]=(FF_Hazard){(300+35*i)*FF_FP,200*FF_FP,0,0,FF_BOMB_FLY,1,0,0};
    g.blasts[0]=(FF_Blast){280*FF_FP,200*FF_FP,20,0};tick(&g,0,0,1);
    for(int i=0;i<4;++i) CHECK(!g.hazards[i].life);
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    g.hazards[0]=(FF_Hazard){345*FF_FP,542*FF_FP,0,0,FF_BOMB_FLY,1,0,0};
    tick(&g,FF_FIRE,0,8);CHECK(!g.hazards[0].life);
    clean(&g);g.players[0].x=300*FF_FP;g.players[0].y=560*FF_FP;
    g.hazards[0]=(FF_Hazard){340*FF_FP,544*FF_FP,0,0,FF_BOMB_FLY,1,0,0};
    tick(&g,FF_PUNCH,0,1);CHECK(!g.hazards[0].life);
    /* A walking bomb turns before stepping off a ledge. */
    clean(&g);arena.imported=true;memset(arena.tiles,0,sizeof(arena.tiles));
    memset(&arena.mask[300][80],FF_PLATFORM,100);
    g.hazards[0]=(FF_Hazard){173*FF_FP,299*FF_FP,FF_FP,0,FF_BOMB_WALK,1,1,0};
    tick(&g,0,0,1);CHECK(g.hazards[0].vx<0);
    /* Falling bombs bounce on their bottom edge (the position is the sprite's centre)
     * from one-way surfaces and solids alike, lower every time,
     * and go off once a bounce is spent; walking bombs never expire. */
    g.hazards[0]=(FF_Hazard){120*FF_FP,294*FF_FP,0,FF_FP,FF_BOMB,1,0,4*FF_FP};
    tick(&g,0,0,1);CHECK(g.hazards[0].life&&g.hazards[0].vy==-4*FF_FP);
    memset(&arena.mask[300][80],FF_SOLID,100);
    g.hazards[0]=(FF_Hazard){120*FF_FP,294*FF_FP,0,FF_FP,FF_BOMB,1,0,4*FF_FP};
    tick(&g,0,0,1);CHECK(g.hazards[0].life&&g.hazards[0].vy==-4*FF_FP);
    g.players[0].active=g.players[1].active=0;   /* nobody falls out of this floorless arena meanwhile */
    int top=g.hazards[0].y,bounces=1,ticks=1;
    while(g.hazards[0].life&&ticks<2000) {
        int before=g.hazards[0].vy;tick(&g,0,0,1);++ticks;
        if(g.hazards[0].life&&before>=0&&g.hazards[0].vy<0) {CHECK(-g.hazards[0].vy<4*FF_FP);++bounces;}
        if(g.hazards[0].life&&g.hazards[0].y<top) top=g.hazards[0].y;
    }
    CHECK(!g.hazards[0].life&&g.blasts[0].life&&bounces>5&&top<265*FF_FP);
    clean(&g);arena.imported=true;memset(arena.tiles,0,sizeof(arena.tiles));
    memset(&arena.mask[300][80],FF_SOLID,100);
    g.hazards[0]=(FF_Hazard){130*FF_FP,299*FF_FP,FF_FP,0,FF_BOMB_WALK,1,1,0};
    g.players[0].active=g.players[1].active=0;
    tick(&g,0,0,3000);CHECK(g.hazards[0].life);
    /* Scheduled hazards use the arena's actual bonus points and seeded RNG. */
    clean(&g);arena.bonus_count=1;arena.bonuses[0]=(FF_Point){400,100};
    g.trap_wait=1;FF_Game replay=g;
    tick(&g,0,0,1);tick(&replay,0,0,1);CHECK(ff_game_hash(&g)==ff_game_hash(&replay));
    CHECK(g.hazards[0].life&&g.hazards[0].y>=100*FF_FP&&g.trap_wait>=200);
    CHECK(g.hazards[0].kind>=FF_BOMB&&g.hazards[0].kind<=FF_BOMB_FLY);
    tick(&g,0,0,1800);tick(&replay,0,0,1800);CHECK(ff_game_hash(&g)==ff_game_hash(&replay));
}
static void imported_weapon_geometry(void) {
    FF_Game g;clean(&g);FF_Player *p=&g.players[0];
    p->x=200*FF_FP;p->y=300*FF_FP;p->weapon=FF_ICE;p->ammo=1;
    arena.muzzles[0][FF_ICE][0]=(FF_Point){30,-11};
    tick(&g,FF_FIRE,0,1);CHECK(g.shots[0].life);
    CHECK(g.shots[0].x==p->x+30*FF_FP+100*FF_FP/8);
    CHECK(g.shots[0].y==p->y-11*FF_FP);
    memset(g.shots,0,sizeof(g.shots));p->facing=-1;p->cooldown=0;p->weapon=FF_ICE;p->ammo=1;
    arena.muzzles[0][FF_ICE][1]=(FF_Point){-29,-10};
    tick(&g,FF_FIRE,0,1);CHECK(g.shots[0].x==p->x-29*FF_FP-100*FF_FP/8);
    CHECK(g.shots[0].y==p->y-10*FF_FP);
    /* Imported blasts grow with the artwork, rather than hitting the full radius immediately. */
    clean(&g);arena.imported=true;arena.blast_sprite.count=2;
    arena.blast_boxes[0]=(FF_Box){-10,-10,20,20};arena.blast_boxes[1]=(FF_Box){-32,-32,64,64};
    g.players[0].x=340*FF_FP;g.players[0].y=400*FF_FP;
    g.blasts[0]=(FF_Blast){300*FF_FP,384*FF_FP,20,0};
    tick(&g,0,0,10);CHECK(g.players[0].health==100);
    tick(&g,0,0,1);CHECK(g.players[0].health==92);
    tick(&g,0,0,9);CHECK(g.players[0].health==92&&!g.blasts[0].life);
}
static void reference_jump(void) {
    FF_Game g;clean(&g);g.players[0].x=100*FF_FP;g.players[0].y=560*FF_FP;g.players[0].grounded=1;
    int top=g.players[0].y;tick(&g,FF_JUMP,0,1);
    for(int i=0;i<44;++i) {if(g.players[0].y<top) top=g.players[0].y;tick(&g,0,0,1);}
    CHECK(560*FF_FP-top>=63*FF_FP&&560*FF_FP-top<=64*FF_FP);
    CHECK(g.players[0].grounded);
    tick(&g,FF_RIGHT,0,20);CHECK(g.players[0].vx==25*FF_FP/8);
    /* The unmodified Wine original repeatedly jumps while Up remains held. */
    clean(&g);g.players[0].x=100*FF_FP;g.players[0].y=560*FF_FP;g.players[0].grounded=1;
    int takeoffs=0;
    for(int i=0;i<100;++i) {int grounded=g.players[0].grounded;tick(&g,FF_JUMP,0,1);if(grounded&&g.players[0].vy<0) ++takeoffs;}
    CHECK(takeoffs==3);
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
    p=&g.players[0];p->x=400*FF_FP;p->y=116*FF_FP;p->vy=0;p->health=50;   /* any kind is wanted */
    tick(&g,0,0,1);CHECK(!g.pickups[0].active&&!g.pickups[0].kind);
    /* Consumed imported bonuses wait for the global timer, not a per-item respawn. */
    g.pickup_wait=500;tick(&g,0,0,301);CHECK(!g.pickups[0].kind);
}
static void tick4(FF_Game *g,const uint8_t in[FF_PLAYERS],int n) {while(n--) ff_game_tick(g,&arena,in);}
static void four_players(void) {
    FF_Game g;ff_arena_practice(&arena);arena.bonus_count=0;
    /* Free for all: seats join independently, an eliminated furry stays out. */
    ff_game_setup(&g,&arena,5,15,FF_FFA);memset(g.pickups,0,sizeof(g.pickups));
    for(int i=0;i<4;++i) {CHECK(g.players[i].active);CHECK(g.players[i].lives==3);CHECK(g.players[i].team==i);}
    CHECK(g.players[2].x==320*FF_FP&&g.players[3].x==480*FF_FP);
    place(&g,0,300);place(&g,1,330);place(&g,2,100);place(&g,3,700);
    g.players[0].facing=1;g.players[1].health=12;g.players[1].lives=1;
    uint8_t punch[FF_PLAYERS]={FF_PUNCH};tick4(&g,punch,1);
    CHECK(!g.players[1].lives);CHECK(g.winner==-1);
    uint8_t idle[FF_PLAYERS]={0};tick4(&g,idle,200);
    CHECK(!g.players[1].lives);CHECK(g.winner==-1);
    /* Out players are neither hit nor targeted, and do not move. */
    int32_t out_x=g.players[1].x;place(&g,0,300);g.players[0].facing=1;
    g.players[1].x=out_x;tick4(&g,punch,1);CHECK(g.players[1].health==0||g.players[1].x==out_x);
    g.players[2].health=1;g.players[2].lives=1;g.players[3].health=1;g.players[3].lives=1;
    place(&g,0,300);place(&g,2,330);place(&g,3,700);g.players[0].facing=1;g.players[0].cooldown=0;
    tick4(&g,punch,1);CHECK(g.winner==-1);
    place(&g,0,670);place(&g,3,700);g.players[0].facing=1;g.players[0].cooldown=0;
    tick4(&g,punch,1);CHECK(g.winner==0);CHECK(g.players[0].score==1);
    for(int i=1;i<4;++i) CHECK(g.players[i].score==0);
    tick4(&g,idle,150);CHECK(g.winner==-1);for(int i=0;i<4;++i) CHECK(g.players[i].lives==3&&g.players[i].active);
    CHECK(g.players[0].score==1);
    /* Three seats: the empty seat never plays, is never hit and never wins. */
    ff_game_setup(&g,&arena,5,1|4|8,FF_FFA);memset(g.pickups,0,sizeof(g.pickups));
    CHECK(!g.players[1].active&&!g.players[1].lives);
    uint8_t move[FF_PLAYERS]={0,FF_RIGHT};int32_t idle_x=g.players[1].x;tick4(&g,move,10);CHECK(g.players[1].x==idle_x);
    /* 2v2: even seats against odd seats, no friendly fists or shots. */
    ff_game_setup(&g,&arena,5,15,FF_TEAMS);memset(g.pickups,0,sizeof(g.pickups));
    CHECK(g.players[0].team==0&&g.players[2].team==0&&g.players[1].team==1&&g.players[3].team==1);
    place(&g,0,300);place(&g,2,330);place(&g,1,100);place(&g,3,700);g.players[0].facing=1;
    tick4(&g,punch,1);CHECK(g.players[2].health==100);
    place(&g,0,300);place(&g,2,360);g.players[0].weapon=FF_ICE;g.players[0].ammo=1;
    uint8_t fire[FF_PLAYERS]={FF_FIRE};tick4(&g,fire,8);CHECK(g.players[2].health==100);
    /* Rockets home on the nearest opponent, never on a teammate. */
    memset(arena.tiles,0,sizeof(arena.tiles));
    place(&g,0,200);g.players[0].y=400*FF_FP;place(&g,2,260);g.players[2].y=400*FF_FP;
    place(&g,1,600);g.players[1].y=200*FF_FP;place(&g,3,700);g.players[3].y=550*FF_FP;
    memset(g.shots,0,sizeof(g.shots));g.players[0].weapon=FF_ROCKET;g.players[0].ammo=1;g.players[0].cooldown=0;
    tick4(&g,fire,1);CHECK(g.shots[0].life&&g.shots[0].vy<0);
    tick4(&g,idle,5);CHECK(g.shots[0].vy<0);
    ff_arena_practice(&arena);arena.bonus_count=0;
    /* The team with a furry standing wins; both of its players score. */
    ff_game_setup(&g,&arena,5,15,FF_TEAMS);memset(g.pickups,0,sizeof(g.pickups));
    g.players[1].lives=0;g.players[3].lives=1;g.players[3].health=1;
    place(&g,0,300);place(&g,3,330);place(&g,2,100);g.players[0].facing=1;
    tick4(&g,punch,1);CHECK(g.winner==FF_TEAM_WIN);
    CHECK(g.players[0].score==1&&g.players[2].score==1&&g.players[1].score==0&&g.players[3].score==0);
    /* Four-player replays stay deterministic. */
    FF_Game a,b;ff_game_setup(&a,&arena,9,15,FF_FFA);b=a;uint32_t r=3;
    for(int i=0;i<5000;++i) {
        r=r*1664525u+1013904223u;uint8_t keys[FF_PLAYERS]={(uint8_t)(r&63),(uint8_t)((r>>6)&63),(uint8_t)((r>>12)&63),(uint8_t)((r>>18)&63)};
        ff_game_tick(&a,&arena,keys);ff_game_tick(&b,&arena,keys);CHECK(ff_game_hash(&a)==ff_game_hash(&b));
    }
}
/* Jan's 2026-10-16 play-test of 0.5.0. */
static void playtest_fixes(void) {
    FF_Game g;clean(&g);g.players[1].active=0;
    /* Walking over a floor spring leaves it alone; landing on it throws you up. */
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_BOUNCE_UP,300,552,32,8,-1};
    FF_Player *p=&g.players[0];p->x=240*FF_FP;p->y=560*FF_FP;p->vx=p->vy=0;p->grounded=1;
    tick(&g,FF_RIGHT,0,60);CHECK(p->x>360*FF_FP);CHECK(!g.device_hit[0]);CHECK(p->grounded);
    p->x=316*FF_FP;p->y=480*FF_FP;p->vx=0;p->grounded=0;
    int thrown=0;for(int i=0;i<40&&!thrown;++i) {tick(&g,0,0,1);thrown=p->vy<0;}
    CHECK(thrown&&g.device_hit[0]&&(g.sounds&FF_SOUND_SPRING));
    /* Jumping makes the original's jump sound. */
    clean(&g);g.players[1].active=0;p=&g.players[0];tick(&g,0,0,60);
    tick(&g,FF_JUMP,0,1);CHECK(p->vy<0&&(g.sounds&FF_SOUND_JUMP));
    /* The ice gun's left muzzle sits inside the shooter's reach: firing left never hurts them. */
    clean(&g);g.players[1].x=700*FF_FP;p=&g.players[0];p->x=400*FF_FP;p->y=560*FF_FP;p->facing=-1;
    arena.muzzles[0][FF_ICE][1]=(FF_Point){-12,-11};p->weapon=FF_ICE;p->ammo=5;
    tick(&g,FF_FIRE|FF_LEFT,0,1);tick(&g,FF_FIRE,0,30);CHECK(p->health==100);CHECK(p->ammo<5);
    /* Up at the water's surface jumps out, onto a ledge level with the water. */
    clean(&g);g.players[1].active=0;p=&g.players[0];
    arena.device_count=1;arena.devices[0]=(FF_Device){FF_WATER,0,480,800,16,-1};
    for(int x=20;x<29;++x) arena.tiles[30][x]=FF_PLATFORM;
    p->x=400*FF_FP;p->y=548*FF_FP;p->vx=p->vy=0;
    tick(&g,FF_JUMP,0,80);tick(&g,0,0,100);CHECK(p->grounded&&p->y==480*FF_FP);
    /* The sky is open: a jetpack carries a furry above the top edge, and it comes back. */
    clean(&g);g.players[1].active=0;p=&g.players[0];p->x=60*FF_FP;p->y=100*FF_FP;p->fuel=300;
    int highest=p->y;for(int i=0;i<120;++i) {tick(&g,FF_FLY,0,1);if(p->y<highest) highest=p->y;}
    CHECK(highest<0);tick(&g,0,0,400);CHECK(p->grounded&&p->y==560*FF_FP&&p->lives==3);
}
/* Jan's second 2026-10-16 play-test, of 0.6.0, against the original's event rows. */
static void second_playtest(void) {
    FF_Game g;FF_Player *p;
    /* Two platforms on one track meet in the middle and both turn back. */
    clean(&g);arena.device_count=2;
    arena.devices[0]=(FF_Device){FF_MOVING_PLATFORM,100,300,48,16,5};arena.paths[0]=(FF_Path){50,600,1,1};
    arena.devices[1]=(FF_Device){FF_MOVING_PLATFORM,400,300,48,16,5};arena.paths[1]=(FF_Path){50,600,1,-1};
    restart(&g);int closest=1000;
    for(int i=0;i<300;++i) {
        tick(&g,0,0,1);int gap=ff_device_position(&arena,&g,1).x-ff_device_position(&arena,&g,0).x-48;
        CHECK(gap>=-2);if(gap<closest) closest=gap;
    }
    CHECK(closest<=0&&g.platform_dir[0]<0&&g.platform_dir[1]>0);
    /* Platforms of different kinds pass each other, as in the original. */
    arena.devices[1].image=6;restart(&g);tick(&g,0,0,300);CHECK(ff_device_position(&arena,&g,0).x>ff_device_position(&arena,&g,1).x);
    /* Steps up to eight pixels are walked up; a taller one stops the furry. */
    clean(&g);g.players[1].active=0;arena.imported=true;memset(arena.tiles,0,sizeof(arena.tiles));
    for(int y=0;y<600;++y) memset(arena.mask[y],0,sizeof(arena.mask[y]));
    for(int y=400;y<600;++y) memset(arena.mask[y],FF_SOLID,800);
    for(int y=396;y<400;++y) memset(&arena.mask[y][300],FF_SOLID,500);
    for(int y=384;y<396;++y) memset(&arena.mask[y][500],FF_SOLID,300);
    p=&g.players[0];p->x=200*FF_FP;p->y=400*FF_FP;p->grounded=1;p->vx=p->vy=0;
    tick(&g,FF_RIGHT,0,150);CHECK(p->y==396*FF_FP&&p->grounded);CHECK(p->x/FF_FP<500-10&&p->x/FF_FP>470);
    /* A furry falling onto the other stands on its head and can jump off it. */
    clean(&g);place(&g,0,300);place(&g,1,300);p=&g.players[0];
    p->y=480*FF_FP;p->grounded=0;tick(&g,0,0,40);
    CHECK(p->y==534*FF_FP&&p->grounded&&g.players[1].y==560*FF_FP);
    tick(&g,FF_JUMP,0,1);CHECK(p->vy<0);
    /* Walking past each other on the same floor stays possible. */
    clean(&g);place(&g,0,300);place(&g,1,330);tick(&g,FF_RIGHT,0,30);CHECK(g.players[0].x>340*FF_FP&&g.players[0].y==560*FF_FP);
    /* Shooting pushes the shooter back: ice by 4, a rocket by 15 (eighths of a pixel per tick). */
    clean(&g);place(&g,0,300);place(&g,1,700);p=&g.players[0];p->facing=1;p->weapon=FF_ICE;p->ammo=5;
    tick(&g,FF_FIRE,0,1);CHECK(p->vx==-4*FF_FP/8+FF_FP/8||p->vx==-4*FF_FP/8);
    clean(&g);place(&g,0,300);place(&g,1,700);p=&g.players[0];p->facing=-1;p->weapon=FF_ROCKET;p->ammo=5;
    tick(&g,FF_FIRE,0,1);CHECK(p->vx>=13*FF_FP/8);tick(&g,0,0,30);CHECK(p->x>310*FF_FP);
    /* Rockets coming down stop on one-way tops, which they cross going up. */
    clean(&g);g.players[1].active=0;for(int x=10;x<20;++x) arena.tiles[20][x]=FF_PLATFORM;
    g.shots[0]=(FF_Shot){240*FF_FP,280*FF_FP,0,57*FF_FP/8,FF_ROCKET,1,100,24,0,0};
    arena.weapons[FF_ROCKET].homing=0;
    for(int i=0;i<10&&g.shots[0].life;++i) tick(&g,0,0,1);
    CHECK(!g.shots[0].life&&g.blasts[0].life&&g.blasts[0].y/FF_FP<=320);
    clean(&g);g.players[1].active=0;for(int x=10;x<20;++x) arena.tiles[20][x]=FF_PLATFORM;arena.weapons[FF_ROCKET].homing=0;
    g.shots[0]=(FF_Shot){240*FF_FP,360*FF_FP,0,-57*FF_FP/8,FF_ROCKET,1,100,8,0,0};
    tick(&g,0,0,10);CHECK(g.shots[0].life&&g.shots[0].y<300*FF_FP);
    /* A bouncing bomb's sprite is centred on it: it bounces with its bottom edge on the floor. */
    clean(&g);g.players[0].active=g.players[1].active=0;
    g.hazards[0]=(FF_Hazard){400*FF_FP,500*FF_FP,0,0,FF_BOMB,1,0,4*FF_FP};
    int lowest=0;for(int i=0;i<400&&g.hazards[0].life;++i) {tick(&g,0,0,1);if(g.hazards[0].y>lowest) lowest=g.hazards[0].y;}
    CHECK(lowest/FF_FP<=560-5);
}
static void determinism(void) {
    FF_Game a,b;clean(&a);b=a;
    uint32_t r=17;
    for(int i=0;i<10000;++i) {
        r=r*1664525u+1013904223u;uint8_t keys[FF_PLAYERS]={(uint8_t)(r&63),(uint8_t)((r>>8)&63)};
        ff_game_tick(&a,&arena,keys);ff_game_tick(&b,&arena,keys);
        CHECK(ff_game_hash(&a)==ff_game_hash(&b));
        for(int k=0;k<2;++k) {CHECK(a.players[k].ammo>=0);CHECK(a.players[k].health>=0&&a.players[k].health<=100);}
    }
    /* The checksum includes state that will change future input transitions. */
    b.players[0].previous^=FF_JUMP;CHECK(ff_game_hash(&a)!=ff_game_hash(&b));
    printf("replay=%08x\n",ff_game_hash(&a));
}
/* Jan's play-test of 0.7.0, against the original's event rows. */
static void third_playtest(void) {
    FF_Game g;FF_Player *p;
    /* Fire passes through a wall (global rows 385-388 never stop it on the backdrop)
     * and burns on the floor behind it, on top of the ground. */
    clean(&g);place(&g,0,360);place(&g,1,700);p=&g.players[0];p->facing=1;p->weapon=FF_FLAME;p->ammo=5;
    for(int y=30;y<35;++y) arena.tiles[y][24]=FF_SOLID;
    tick(&g,FF_FIRE,0,1);tick(&g,0,0,40);
    int settled=-1;for(int i=0;i<FF_SHOTS;++i) if(g.shots[i].life&&g.shots[i].settled) settled=i;
    CHECK(settled>=0&&g.shots[settled].x>400*FF_FP&&g.shots[settled].y/FF_FP==559);
    /* An explosion throws a furry falling onto it upwards, and one still blinking too. */
    clean(&g);place(&g,0,300);place(&g,1,700);p=&g.players[0];
    p->y=500*FF_FP;p->grounded=0;p->vy=8*FF_FP;p->invulnerable=40;
    g.blasts[0]=(FF_Blast){300*FF_FP,515*FF_FP,20,0};
    tick(&g,0,0,1);CHECK(p->vy==-50*FF_FP/8&&!p->grounded);
    int top=p->y;for(int i=0;i<40;++i) {tick(&g,0,0,1);if(p->y<top) top=p->y;}
    CHECK(top<445*FF_FP);
    /* Sideways the throw replaces a run toward the blast instead of slowing it. */
    clean(&g);place(&g,0,300);place(&g,1,700);p=&g.players[0];p->vx=25*FF_FP/8;
    g.blasts[0]=(FF_Blast){320*FF_FP,545*FF_FP,20,0};
    tick(&g,FF_RIGHT,0,1);CHECK(p->vx==-50*FF_FP/8);
    /* The flying jetpack puffs smoke with its sound every fifth tick, as the original's
     * fly object does (frame rows 26/27). */
    clean(&g);place(&g,0,300);place(&g,1,700);p=&g.players[0];p->fuel=100;
    int sounds=0;for(int i=0;i<11;++i) {tick(&g,FF_FLY,0,1);sounds+=!!(g.sounds&FF_SOUND_JETPACK);}
    int puffs=0;for(int i=0;i<FF_PUFFS;++i) puffs+=g.puffs[i].tick!=0;
    CHECK(sounds==3&&puffs==3&&abs(g.puffs[0].x-300)<2&&g.puffs[2].tick-g.puffs[0].tick==10);
    tick(&g,0,0,5);CHECK(!(g.sounds&FF_SOUND_JETPACK));
}
int main(void) {physics();melee_round();weapons();homing_rockets();persistent_flame_and_impulses();bonuses();arena_devices();marker_collision_and_paths();sensor_body_and_directional_bounces();hazards_and_blasts();imported_weapon_geometry();reference_jump();wind_and_bonus_regions();four_players();playtest_fixes();second_playtest();third_playtest();determinism();printf("%u game checks passed\n",checks);return 0;}
