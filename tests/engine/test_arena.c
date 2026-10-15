#include "game.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} ++checks;} while(0)
static unsigned checks;
static FF_Arena arena;
static bool load(const char *body) {
    FILE *f=fopen("native-test-arena.ff","w");CHECK(f!=NULL);fputs(body,f);fclose(f);
    char error[128];bool ok=ff_arena_load(&arena,"native-test-arena.ff",error,sizeof(error));
    CHECK(remove("native-test-arena.ff")==0);return ok;
}
int main(void) {
    CHECK(load("FFARENA 1\nspawn 100 100\nspawn 200 100\nmask 200 80 32 1\nmask 220 90 20 2\nsprite 0 0 0 0 7\nhot 7 -3 8\ndevice 9 100 200 48 16 4\n"));
    CHECK(arena.imported&&arena.spawn_count==2);CHECK(arena.mask[200][80]==FF_SOLID);CHECK(arena.mask[200][111]==FF_SOLID);CHECK(!arena.mask[200][112]);
    CHECK(arena.mask[220][90]==FF_PLATFORM);CHECK(arena.sprites[0][0][0][0].image[0]==7);CHECK(arena.hot_x[7]==-3);
    CHECK(arena.device_count==1&&arena.devices[0].kind==FF_MOVING_PLATFORM);
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nmask 600 0 1 1\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nmask 200 790 20 1\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nsprite 2 0 0 0 7\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\ndevice 10 0 0 16 16 7\n"));
    CHECK(load("FFARENA 1\nspawn 100 100\nspawn 200 100\ndevice 9 100 200 48 16 4\npath 0 50 200 1 -1\n"));
    CHECK(ff_device_position(&arena,0,50).x==50);
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\npath 0 50 200 1 -1\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\ndevice 9 100 200 48 16 4\npath 0 100 100 1 -1\n"));
    CHECK(load("FFARENA 1\nspawn 100 100\nspawn 200 100\nbonus 120 150\nhazard 3 0 12\nblast 13\nsound 7 14\n"));
    CHECK(arena.bonus_count==1&&arena.bonuses[0].x==120);
    CHECK(arena.hazard_sprites[2][0].image[0]==12&&arena.blast_sprite.image[0]==13&&arena.sound_ids[7]==14);
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nhazard 4 0 12\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nbonus 800 100\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\nblast 1024\n"));
    CHECK(load("FFARENA 1\nspawn 100 100\nspawn 200 100\ndevice 12 80 200 32 128 -1\n"));
    CHECK(arena.devices[0].kind==FF_WIND_UP&&arena.devices[0].image==-1);
    CHECK(!load("FFARENA 2\nspawn 100 100\nspawn 200 100\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\n"));
    CHECK(!load("FFARENA 1\nspawn 100 100\nspawn 200 100\ntruncated"));
    printf("%u arena-format checks passed\n",checks);return 0;
}
