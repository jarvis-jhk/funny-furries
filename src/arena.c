#include "game.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void ff_arena_practice(FF_Arena *a) {
    memset(a, 0, sizeof(*a));
    for (int x=0; x<FF_COLS; ++x) a->tiles[35][x]=FF_SOLID;
    for (int y=3; y<35; ++y) a->tiles[y][0]=a->tiles[y][49]=FF_SOLID;
    for (int x=5; x<20; ++x) a->tiles[27][x]=FF_PLATFORM;
    for (int x=30; x<45; ++x) a->tiles[27][x]=FF_PLATFORM;
    for (int x=17; x<33; ++x) a->tiles[19][x]=FF_PLATFORM;
    a->spawn_count=4;
    a->spawns[0]=(FF_Point){160,520}; a->spawns[1]=(FF_Point){640,520};
    a->spawns[2]=(FF_Point){320,280}; a->spawns[3]=(FF_Point){480,280};
    for (int i=0;i<6;++i) a->pickup_images[i]=-1;
    for (int i=0;i<4;++i) a->shot_images[i]=-1;
    for (int i=0;i<7;++i) a->sound_ids[i]=-1;
}

/* A small bounded text format keeps imported game content separate from code. */
bool ff_arena_load(FF_Arena *a, const char *path, char *error, unsigned capacity) {
    FILE *f=fopen(path,"r");
    if (!f) { snprintf(error,capacity,"Cannot open arena data"); return false; }
    memset(a,0,sizeof(*a));
    for (int i=0;i<6;++i) a->pickup_images[i]=-1;
    for (int i=0;i<4;++i) a->shot_images[i]=-1;
    for (int i=0;i<7;++i) a->sound_ids[i]=-1;
    char line[1024]; int version=0, lines=0; bool ok=true;
    while (fgets(line,sizeof(line),f)) {
        ++lines; int n[10]; unsigned c[2]; char tail;
        if (!strchr(line,'\n') || lines>20000) { ok=false; break; }
        if (lines==1) { ok=sscanf(line,"FFARENA %d %c",&version,&tail)==1 && version==1; if (!ok) break; continue; }
        if (line[0]=='#' || line[0]=='\n') continue;
        if (sscanf(line,"tile %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<0||n[0]>=FF_COLS||n[1]<0||n[1]>=FF_ROWS||n[2]<1||n[2]>2) {ok=false;break;}
            a->tiles[n[1]][n[0]]=(uint8_t)n[2];
        } else if (sscanf(line,"spawn %d %d %c",&n[0],&n[1],&tail)==2) {
            if(a->spawn_count==FF_SPAWNS||n[0]<12||n[0]>788||n[1]<40||n[1]>560) {ok=false;break;}
            a->spawns[a->spawn_count++]=(FF_Point){n[0],n[1]};
        } else if (sscanf(line,"layer %d %d %d %d %d %d %x %x %c",&n[0],&n[1],&n[2],&n[3],&n[4],&n[5],&c[0],&c[1],&tail)==8) {
            if(a->layer_count==FF_LAYERS||n[0]<-1||n[0]>=FF_IMAGES||n[1]<-32768||n[1]>32767||n[2]<-32768||n[2]>32767||n[3]<1||n[3]>4096||n[4]<1||n[4]>4096||n[5]<0||n[5]>4) {ok=false;break;}
            a->layers[a->layer_count++]=(FF_Layer){n[0],n[1],n[2],n[3],n[4],n[5],{c[0],c[1]}};
        } else if (sscanf(line,"hot %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<0||n[0]>=FF_IMAGES||n[1]<-4096||n[1]>4096||n[2]<-4096||n[2]>4096) {ok=false;break;}
            a->hot_x[n[0]]=n[1];a->hot_y[n[0]]=n[2];
        } else if (sscanf(line,"sprite %d %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&n[4],&tail)==5) {
            if(n[0]<0||n[0]>1||n[1]<0||n[1]>=FF_PARTS||n[2]<0||n[2]>=FF_ANIMS||n[3]<0||n[3]>1||n[4]<0||n[4]>=FF_IMAGES) {ok=false;break;}
            FF_Sequence *s=&a->sprites[n[0]][n[1]][n[2]][n[3]];
            if(s->count==FF_ANIM_FRAMES) {ok=false;break;} s->image[s->count++]=n[4];
        } else if (sscanf(line,"pickup %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>5||n[1]<0||n[1]>=FF_IMAGES) {ok=false;break;} a->pickup_images[n[0]]=n[1];
        } else if (sscanf(line,"shot %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<1||n[0]>3||n[1]<0||n[1]>=FF_IMAGES) {ok=false;break;} a->shot_images[n[0]]=n[1];
        } else if (sscanf(line,"sound %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>6||n[1]<0||n[1]>4096) {ok=false;break;} a->sound_ids[n[0]]=n[1];
        } else {ok=false;break;}
    }
    if(ferror(f)||version!=1||a->spawn_count<2) ok=false;
    fclose(f);
    if(!ok) {snprintf(error,capacity,"Invalid arena data at line %d",lines);return false;}
    a->imported=true;return true;
}
