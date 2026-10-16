#include "game.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#endif

static void asset_defaults(FF_Arena *a) {
    for(int i=0;i<6;++i) a->pickup_images[i]=-1;
    for(int i=0;i<4;++i) a->shot_images[i]=-1;
    for(int i=0;i<FF_SOUNDS;++i) a->sound_ids[i]=-1;
    for(int p=0;p<2;++p) for(int w=1;w<4;++w) for(int d=0;d<2;++d)
        a->muzzles[p][w][d]=(FF_Point){d?-16:16,-18};
    for(int i=0;i<11;++i) a->hud.digits[i]=-1;
    for(int i=0;i<3;++i) a->hud.bar[i]=-1;
}
static bool add_frame(FF_Sequence *s,int speed,int image) {
    if(s->count==FF_ANIM_FRAMES||(s->count&&s->speed!=speed)) return false;
    s->speed=speed;s->image[s->count++]=image;return true;
}
void ff_arena_practice(FF_Arena *a) {
    memset(a, 0, sizeof(*a));
    for (int x=0; x<FF_COLS; ++x) a->tiles[35][x]=FF_SOLID;
    for (int y=3; y<35; ++y) a->tiles[y][0]=a->tiles[y][49]=FF_SOLID;
    for (int x=5; x<20; ++x) a->tiles[27][x]=FF_PLATFORM;
    for (int x=30; x<45; ++x) a->tiles[27][x]=FF_PLATFORM;
    for (int x=17; x<33; ++x) a->tiles[19][x]=FF_PLATFORM;
    a->spawn_count=4;
    a->bonus_count=2;a->bonuses[0]=(FF_Point){350,200};a->bonuses[1]=(FF_Point){450,200};
    a->spawns[0]=(FF_Point){160,520}; a->spawns[1]=(FF_Point){640,520};
    a->spawns[2]=(FF_Point){320,280}; a->spawns[3]=(FF_Point){480,280};
    asset_defaults(a);
}

/* A small bounded text format keeps imported game content separate from code. */
bool ff_arena_load(FF_Arena *a, const char *path, char *error, unsigned capacity) {
#ifdef _WIN32
    wchar_t wide[4096];
    FILE *f=NULL;
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,4096)>0) f=_wfopen(wide,L"r");
#else
    FILE *f=fopen(path,"r");
#endif
    if (!f) { snprintf(error,capacity,"Cannot open arena data"); return false; }
    memset(a,0,sizeof(*a));
    asset_defaults(a);
    char line[1024]; int version=0, lines=0; bool ok=true;
    while (fgets(line,sizeof(line),f)) {
        ++lines; int n[10]; unsigned c[2]; char tail;
        if (!strchr(line,'\n') || lines>60000) { ok=false; break; }
        if (lines==1) { ok=sscanf(line,"FFARENA %d %c",&version,&tail)==1 && version==1; if (!ok) break; continue; }
        if (line[0]=='#' || line[0]=='\n') continue;
        if (sscanf(line,"tile %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<0||n[0]>=FF_COLS||n[1]<0||n[1]>=FF_ROWS||n[2]<1||n[2]>2) {ok=false;break;}
            a->tiles[n[1]][n[0]]=(uint8_t)n[2];
        } else if (sscanf(line,"mask %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&tail)==4) {
            if(n[0]<0||n[0]>=FF_H||n[1]<0||n[1]>=FF_W||n[2]<1||n[2]>FF_W-n[1]||n[3]<1||n[3]>2) {ok=false;break;}
            memset(&a->mask[n[0]][n[1]],n[3],(size_t)n[2]);
        } else if (sscanf(line,"spawn %d %d %c",&n[0],&n[1],&tail)==2) {
            if(a->spawn_count==FF_SPAWNS||n[0]<12||n[0]>788||n[1]<32||n[1]>560) {ok=false;break;}
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
        } else if (sscanf(line,"muzzle %d %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&n[4],&tail)==5) {
            if(n[0]<0||n[0]>1||n[1]<1||n[1]>3||n[2]<0||n[2]>1||
               n[3]<-4096||n[3]>4096||n[4]<-4096||n[4]>4096) {ok=false;break;}
            a->muzzles[n[0]][n[1]][n[2]]=(FF_Point){n[3],n[4]};
        } else if (sscanf(line,"device %d %d %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&n[4],&n[5],&tail)==6) {
            if(a->device_count==FF_DEVICES||n[0]<1||n[0]>FF_WIND_UP||n[1]<-4096||n[1]>4096||n[2]<-4096||n[2]>4096||n[3]<1||n[3]>1024||n[4]<1||n[4]>1024||n[5]<-1||n[5]>=FF_IMAGES||(n[0]>=FF_WIND_LEFT?n[5]!=-1:n[5]<0)) {ok=false;break;}
            a->devices[a->device_count++]=(FF_Device){n[0],n[1],n[2],n[3],n[4],n[5]};
        } else if (sscanf(line,"path %d %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&n[4],&tail)==5) {
            if(n[0]<0||n[0]>=a->device_count||a->devices[n[0]].kind!=FF_MOVING_PLATFORM||
               a->paths[n[0]].speed||n[1]<-4096||n[2]>4096||n[1]>=n[2]||
               a->devices[n[0]].x<n[1]||a->devices[n[0]].x>n[2]||
               n[3]<1||n[3]>8||(n[4]!=-1&&n[4]!=1)) {ok=false;break;}
            a->paths[n[0]]=(FF_Path){n[1],n[2],n[3],n[4]};
        } else if (sscanf(line,"bonus %d %d %c",&n[0],&n[1],&tail)==2) {
            if(a->bonus_count==FF_SPAWNS||n[0]<0||n[0]>=FF_W||n[1]<0||n[1]>=560) {ok=false;break;}
            a->bonuses[a->bonus_count++]=(FF_Point){n[0],n[1]};
        } else if (sscanf(line,"hazard %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<1||n[0]>3||n[1]<0||n[1]>1||n[2]<0||n[2]>=FF_IMAGES) {ok=false;break;}
            FF_Sequence *s=&a->hazard_sprites[n[0]-1][n[1]];
            if(s->count==FF_ANIM_FRAMES) {ok=false;break;} s->image[s->count++]=n[2];
        } else if (sscanf(line,"blast %d %c",&n[0],&tail)==1) {
            if(n[0]<0||n[0]>=FF_IMAGES||a->blast_sprite.count==FF_ANIM_FRAMES) {ok=false;break;}
            a->blast_sprite.image[a->blast_sprite.count++]=n[0];
        } else if (sscanf(line,"blastbox %d %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&n[4],&tail)==5) {
            if(n[0]<0||n[0]>=a->blast_sprite.count||n[1]<-4096||n[1]>4096||
               n[2]<-4096||n[2]>4096||n[3]<1||n[3]>4096||n[4]<1||n[4]>4096) {ok=false;break;}
            a->blast_boxes[n[0]]=(FF_Box){n[1],n[2],n[3],n[4]};
        } else if (sscanf(line,"fire %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>1||n[1]<0||n[1]>=FF_IMAGES) {ok=false;break;}
            FF_Sequence *s=&a->fire_sprites[n[0]];
            if(s->count==FF_ANIM_FRAMES) {ok=false;break;} s->image[s->count++]=n[1];
        } else if (sscanf(line,"devanim %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&tail)==4) {
            if(n[0]<1||n[0]>FF_WIND_UP||n[1]<0||n[1]>1||n[2]<1||n[2]>100||n[3]<0||n[3]>=FF_IMAGES||
               !add_frame(&a->device_sprites[n[0]][n[1]],n[2],n[3])) {ok=false;break;}
        } else if (sscanf(line,"pickanim %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<1||n[0]>5||n[1]<1||n[1]>100||n[2]<0||n[2]>=FF_IMAGES||
               !add_frame(&a->pickup_sprites[n[0]],n[1],n[2])) {ok=false;break;}
        } else if (sscanf(line,"hazardspeed %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<1||n[0]>3||n[1]<1||n[1]>100) {ok=false;break;}
            a->hazard_sprites[n[0]-1][0].speed=a->hazard_sprites[n[0]-1][1].speed=n[1];
        } else if (sscanf(line,"hudfield %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&tail)==4) {
            if(n[0]<0||n[0]>1||n[1]<0||n[1]>=FF_HUD_FIELDS||n[2]<0||n[2]>FF_W||n[3]<0||n[3]>FF_H) {ok=false;break;}
            a->hud.field[n[0]][n[1]]=(FF_Point){n[2],n[3]};
        } else if (sscanf(line,"huddigit %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>10||n[1]<0||n[1]>=FF_IMAGES) {ok=false;break;}
            a->hud.digits[n[0]]=n[1];
        } else if (sscanf(line,"hudweapon %d %d %d %c",&n[0],&n[1],&n[2],&tail)==3) {
            if(n[0]<0||n[0]>3||n[1]<1||n[1]>100||n[2]<0||n[2]>=FF_IMAGES||
               !add_frame(&a->hud.weapon[n[0]],n[1],n[2])) {ok=false;break;}
        } else if (sscanf(line,"hudbar %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>2||n[1]<0||n[1]>=FF_IMAGES) {ok=false;break;}
            a->hud.bar[n[0]]=n[1];
        } else if (sscanf(line,"hudbarbox %d %d %d %d %c",&n[0],&n[1],&n[2],&n[3],&tail)==4) {
            if(n[0]<0||n[0]>FF_W||n[1]<0||n[1]>FF_H||n[2]<0||n[2]>n[0]||n[3]<n[0]||n[3]>FF_W) {ok=false;break;}
            a->hud.bar_at=(FF_Point){n[0],n[1]};a->hud.bar_left=n[2];a->hud.bar_right=n[3];
        } else if (sscanf(line,"hudfuel %x %d %d %c",&c[0],&n[0],&n[1],&tail)==3) {
            if(c[0]>0xffffff||n[0]<1||n[0]>FF_W||n[1]<1||n[1]>40) {ok=false;break;}
            a->hud.fuel_color=c[0];a->hud.fuel_width=n[0];a->hud.fuel_height=n[1];
        } else if (sscanf(line,"sound %d %d %c",&n[0],&n[1],&tail)==2) {
            if(n[0]<0||n[0]>=FF_SOUNDS||n[1]<0||n[1]>4096) {ok=false;break;} a->sound_ids[n[0]]=n[1];
        } else {ok=false;break;}
    }
    if(ferror(f)||version!=1||a->spawn_count<2) ok=false;
    a->hud.on=true;
    for(int i=0;i<10;++i) if(a->hud.digits[i]<0) a->hud.on=false;
    fclose(f);
    if(!ok) {snprintf(error,capacity,"Invalid arena data at line %d",lines);return false;}
    a->imported=true;return true;
}
