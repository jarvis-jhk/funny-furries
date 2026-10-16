#include "mod.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#endif
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
static char dir[512];
static void write_file(const char *name,const char *text) {
    char path[600];snprintf(path,sizeof(path),"%s/%s",dir,name);
    FILE *f=fopen(path,"w");if(!f) {perror(path);exit(1);}
    fputs(text,f);fclose(f);
}
/* A 4x2 picture: black, blue, white, transparent on both rows. */
static bool reader(const char *path,int *w,int *h,uint8_t **rgba) {
    (void)path;*w=4;*h=2;*rgba=malloc(32);
    static const uint8_t px[16]={0,0,0,255, 0,0,255,255, 255,255,255,255, 0,0,0,0};
    memcpy(*rgba,px,16);memcpy(*rgba+16,px,16);return true;
}
static void tick(FF_Game *g,uint8_t a,int n) {uint8_t in[FF_PLAYERS]={a,0};while(n--) ff_game_tick(g,&arena,in);}
static void weapons(void) {
    FF_Mods m={0};char error[256];
    ff_arena_practice(&arena);FF_Arena before=arena;
    write_file("mod.ff","FFMOD 1\nimage 1024 shot.png\nimage 40 skin.png 3 4\nsound 9 zap.wav\n"
        "weapon 4 name=snow_balls speed=50 gravity=20 pellets=3 spread=2 bounces=1 ammo=10 shot=1024\n"
        "weapon 5 name=boom speed=40 gravity=28 blast=1 bounces=2 damage=0\nrule lives 5\nrule gravity 28\n");
    CHECK(ff_mod_apply(&arena,&m,dir,"test",error,sizeof(error)));
    CHECK(arena.rules.weapons==5&&arena.rules.lives==5&&arena.rules.gravity==28);
    CHECK(!strcmp(arena.weapons[4].name,"SNOW-BALLS")&&arena.weapons[4].pellets==3&&arena.weapons[4].shot_image==1024);
    CHECK(arena.weapons[4].max_ammo==20);   /* a new weapon starts from the defaults */
    CHECK(m.image_path[1024]&&m.center[1024]&&!m.center[40]&&arena.hot_x[40]==3);
    CHECK(m.sound_path[9]&&!strcmp(m.names,"TEST"));
    CHECK(ff_pickup_kinds(&arena)==7&&ff_pickup_weapon(6)==4&&ff_pickup_weapon(7)==5&&ff_pickup_weapon(4)==0);
    CHECK(!memcmp(&before.weapons[1],&arena.weapons[1],3*sizeof(FF_Weapon)));
    /* Three pellets per pull, one ammo each pull, fanned out and falling. */
    FF_Game g;ff_game_setup(&g,&arena,7,3,FF_FFA);memset(g.pickups,0,sizeof(g.pickups));
    CHECK(g.players[0].lives==5);
    g.players[1].x=760*FF_FP;g.players[0].weapon=4;g.players[0].ammo=10;
    tick(&g,0,60);tick(&g,FF_FIRE,1);
    int shots=0;for(int i=0;i<FF_SHOTS;++i) shots+=g.shots[i].life>0;
    CHECK(shots==3&&g.players[0].ammo==9);
    /* Gravity already acted once: the middle pellet falls at 20, the others fan around it. */
    CHECK(g.shots[1].vy==20&&g.shots[0].vy+g.shots[2].vy==40&&g.shots[0].vy!=g.shots[2].vy);
    int32_t vy=g.shots[1].vy;tick(&g,0,1);CHECK(g.shots[1].vy==vy+20);
    /* They bounce off the floor once, then end on the next floor contact. */
    int bounced=0;for(int t=0;t<140;++t) {tick(&g,0,1);for(int i=0;i<3;++i) if(g.shots[i].bounced) bounced|=1<<i;}
    CHECK(bounced==7);CHECK(!g.shots[0].life&&!g.shots[1].life&&!g.shots[2].life);
    /* The present explodes where it ends. */
    ff_game_setup(&g,&arena,7,3,FF_FFA);memset(g.pickups,0,sizeof(g.pickups));
    g.players[1].x=760*FF_FP;g.players[0].weapon=5;g.players[0].ammo=2;
    tick(&g,0,60);tick(&g,FF_FIRE,1);
    bool blasted=false;for(int t=0;t<200&&!blasted;++t) {tick(&g,0,1);for(int i=0;i<FF_BLASTS;++i) blasted|=g.blasts[i].life>0;}
    CHECK(blasted);
    /* Picking up kind 6 gives weapon 4 with its own ammo. */
    ff_game_setup(&g,&arena,7,3,FF_FFA);memset(g.pickups,0,sizeof(g.pickups));
    tick(&g,0,60);
    g.pickups[0]=(FF_Pickup){g.players[0].x/FF_FP,g.players[0].y/FF_FP-16,6,1,0};
    tick(&g,0,1);CHECK(g.players[0].weapon==4&&g.players[0].ammo==10);
    ff_mods_free(&m);
}
static void broken_mods(void) {
    static const char *const bad[]={
        "FFMOD 2\n","FFMOD 1\nimage 1024 ../escape.png\n","FFMOD 1\nimage 1024 /etc/passwd\n",
        "FFMOD 1\nweapon 6 speed=10\n","FFMOD 1\nweapon 4 speed=9999\n","FFMOD 1\nweapon 4 colour=3\n",
        "FFMOD 1\nrule lives 0\n","FFMOD 1\nlevel missing.ff\n","FFMOD 1\nscript run.lua\n",
    };
    for(size_t i=0;i<sizeof(bad)/sizeof(bad[0]);++i) {
        FF_Mods m={0};char error[256]="";ff_arena_practice(&arena);
        write_file("mod.ff",bad[i]);
        CHECK(!ff_mod_apply(&arena,&m,dir,"bad",error,sizeof(error)));CHECK(error[0]);
        ff_mods_free(&m);
    }
}
static void levels(void) {
    FF_Mods m={0};char error[256],path[600];
    ff_arena_practice(&arena);
    /* Devices copy the base arena's look: the first of each kind. */
    arena.devices[0]=(FF_Device){FF_BOUNCE_UP,0,0,32,16,28};arena.devices[1]=(FF_Device){FF_MOVING_PLATFORM,0,0,48,16,183};arena.device_count=2;
    arena.hud.on=arena.hud.has_panel=true;arena.hud.panel=(FF_Layer){298,0,560,800,40,1,{0,0}};
    write_file("level.ff","FFLEVEL 1\nname Test Peak\npicture sky.png 0 0\nfill 102030 0 0 800 10\n"
        "collision c.png 100 200\nsolid 0 540 800 20\nplatform 300 400 50 2\nspawn 100 540\nspawn 700 540\n"
        "bonus 400 300\nplace spring-up 10 524\nplace wind-up 352 300 96 260\nmoving 400 100 300 500 2\nscoreboard\n");
    write_file("mod.ff","FFMOD 1\nlevel level.ff\n");
    CHECK(ff_mod_apply(&arena,&m,dir,"levels",error,sizeof(error)));
    CHECK(m.level_count==1&&!strcmp(m.level_name[0],"TEST PEAK"));
    snprintf(path,sizeof(path),"%s/level.ff",dir);
    CHECK(ff_level_apply(&arena,&m,path,reader,error,sizeof(error)));
    CHECK(arena.imported&&arena.spawn_count==2&&arena.bonus_count==1&&arena.device_count==3);
    CHECK(arena.layers[0].image==FF_MOD_IMAGES&&arena.layers[0].w==4&&arena.layers[1].kind==2);
    CHECK(arena.layers[2].image==298&&arena.hud.on);   /* the panel comes last */
    CHECK(arena.mask[200][100]==FF_SOLID&&arena.mask[200][101]==FF_PLATFORM&&!arena.mask[200][102]&&!arena.mask[200][103]);
    CHECK(arena.mask[545][0]==FF_SOLID&&arena.mask[401][320]==FF_PLATFORM&&!arena.mask[402][320]);
    CHECK(arena.devices[0].image==28&&arena.devices[0].w==32&&arena.devices[1].w==96&&arena.devices[1].image==-1);
    CHECK(arena.devices[2].kind==FF_MOVING_PLATFORM&&arena.paths[2].speed==2&&arena.paths[2].min_x==300);
    /* A level runs, and without a scoreboard line keeps the plain HUD. */
    FF_Game g;ff_game_setup(&g,&arena,3,3,FF_FFA);uint8_t in[FF_PLAYERS]={0};
    for(int t=0;t<500;++t) ff_game_tick(&g,&arena,in);
    CHECK(g.players[0].grounded&&g.players[0].y==540*FF_FP);
    write_file("level.ff","FFLEVEL 1\nname Bare\nsolid 0 540 800 20\nspawn 100 540\nspawn 700 540\n");
    CHECK(ff_level_apply(&arena,&m,path,reader,error,sizeof(error))&&!arena.hud.on);
    write_file("level.ff","FFLEVEL 1\nname One spawn\nspawn 100 540\n");
    CHECK(!ff_level_apply(&arena,&m,path,reader,error,sizeof(error)));
    write_file("level.ff","FFLEVEL 1\nname Unknown device\nplace teleporter 1 1\nspawn 100 540\nspawn 700 540\n");
    CHECK(!ff_level_apply(&arena,&m,path,reader,error,sizeof(error)));
    /* On the practice base there is no spring to copy: the level still loads, without it. */
    ff_arena_practice(&arena);
    write_file("level.ff","FFLEVEL 1\nname No springs\nplace spring-up 1 1\nplace wind-up 0 0 10 10\nspawn 100 540\nspawn 700 540\n");
    CHECK(ff_level_apply(&arena,&m,path,reader,error,sizeof(error))&&arena.device_count==1);
    ff_mods_free(&m);
}
int main(void) {
    const char *tmp=getenv("TMPDIR");
    snprintf(dir,sizeof(dir),"%s/ff-mod-test-%d",tmp&&*tmp?tmp:"/tmp",(int)(rand()%100000));
#ifdef _WIN32
    snprintf(dir,sizeof(dir),"ff-mod-test");
    _mkdir(dir);
#else
    char command[600];snprintf(command,sizeof(command),"mkdir -p '%s'",dir);if(system(command)) return 1;
#endif
    weapons();broken_mods();levels();
    printf("%u checks passed\n",checks);
    return 0;
}
