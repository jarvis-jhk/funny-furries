#include "game.h"
#include "input.h"
#include "fault.h"
#include <SDL_image.h>
#include <SDL_mixer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

typedef struct { SDL_Texture *texture; int w,h; } Image;
typedef struct {
    SDL_Window *window;SDL_Renderer *renderer;SDL_Texture *scene,*backdrop; FF_Input input;
    Image images[FF_IMAGES]; Mix_Chunk *sounds[7]; bool audio;
    const char *assets;
} App;
static const uint8_t font[][5]={
 {14,17,19,21,14},{4,12,4,4,14},{14,17,2,4,31},{30,1,6,1,30},{2,6,10,31,2},
 {31,16,30,1,30},{14,16,30,17,14},{31,1,2,4,4},{14,17,14,17,14},{14,17,15,1,14},
 {14,17,31,17,17},{30,17,30,17,30},{15,16,16,16,15},{30,17,17,17,30},{31,16,30,16,31},
 {31,16,30,16,16},{15,16,19,17,15},{17,17,31,17,17},{14,4,4,4,14},{7,2,2,18,12},
 {17,18,28,18,17},{16,16,16,16,31},{17,27,21,17,17},{17,25,21,19,17},{14,17,17,17,14},
 {30,17,30,16,16},{14,17,21,18,13},{30,17,30,18,17},{15,16,14,1,30},{31,4,4,4,4},
 {17,17,17,17,14},{17,17,17,10,4},{17,17,21,27,17},{17,10,4,10,17},{17,10,4,4,4},{31,2,4,8,31}
};
static void color(App *app,int r,int g,int b) {SDL_SetRenderDrawColor(app->renderer,(Uint8)r,(Uint8)g,(Uint8)b,255);}
static void rect(App *app,int x,int y,int w,int h) {SDL_Rect r={x,y,w,h};SDL_RenderFillRect(app->renderer,&r);}
static void text(App *app,int x,int y,int scale,const char *s) {
    for(;*s;++s,x+=6*scale) {
        int c=*s,index=c>='0'&&c<='9'?c-'0':c>='A'&&c<='Z'?c-'A'+10:-1;
        if(index>=0) for(int yy=0;yy<5;++yy) for(int xx=0;xx<5;++xx)
            if(font[index][yy]&(1<<(4-xx))) rect(app,x+xx*scale,y+yy*scale,scale,scale);
        if(c=='-') rect(app,x,y+2*scale,5*scale,scale);
        if(c==':') {rect(app,x+2*scale,y+scale,scale,scale);rect(app,x+2*scale,y+3*scale,scale,scale);}
        if(c=='/') for(int yy=0;yy<5;++yy) rect(app,x+(4-yy)*scale,y+yy*scale,scale,scale);
    }
}
static Image *load_image(App *app,int id) {
    if(id<0||id>=FF_IMAGES||!app->assets) return NULL;
    Image *image=&app->images[id];
    if(image->texture) return image;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/image-21-%d.png",app->assets,id)>=(int)sizeof(path)) return NULL;
    SDL_Surface *s=IMG_Load(path);if(!s) return NULL;
    image->w=s->w;image->h=s->h;image->texture=SDL_CreateTextureFromSurface(app->renderer,s);SDL_FreeSurface(s);
    return image->texture?image:NULL;
}
static void sprite(App *app,const FF_Arena *a,int id,int x,int y) {
    Image *image=load_image(app,id);if(!image) return;
    SDL_Rect dest={x-a->hot_x[id],y-a->hot_y[id],image->w,image->h};
    SDL_RenderCopy(app->renderer,image->texture,NULL,&dest);
}
static void rgb(App *app,uint32_t value) {color(app,(value>>16)&255,(value>>8)&255,value&255);}
static void background(App *app,const FF_Arena *a) {
    color(app,25,43,66);SDL_RenderClear(app->renderer);
    if(a->imported) {
        for(int i=0;i<a->layer_count;++i) {
            const FF_Layer *l=&a->layers[i];SDL_Rect dest={l->x,l->y,l->w,l->h};
            Image *image=load_image(app,l->image);
            if(l->kind==0&&image) {SDL_RenderCopy(app->renderer,image->texture,NULL,&dest);}
            else if(l->kind==1&&image) {
                SDL_RenderSetClipRect(app->renderer,&dest);
                for(int y=l->y;y<l->y+l->h;y+=image->h) for(int x=l->x;x<l->x+l->w;x+=image->w) {
                    SDL_Rect d={x,y,image->w,image->h};SDL_RenderCopy(app->renderer,image->texture,NULL,&d);
                }
                SDL_RenderSetClipRect(app->renderer,NULL);
            } else {
                rgb(app,l->color[0]);rect(app,l->x,l->y,l->w,l->h);
                if(l->kind>=3) {
                    int extent=l->kind==3?l->h:l->w;
                    for(int j=0;j<extent;++j) {
                        uint32_t mixed=0;
                        for(int shift=0;shift<=16;shift+=8) {
                            int v0=(l->color[0]>>shift)&255,v1=(l->color[1]>>shift)&255;
                            mixed|=(uint32_t)(v0+(v1-v0)*j/(extent>1?extent-1:1))<<shift;
                        }
                        rgb(app,mixed);rect(app,l->x+(l->kind==4?j:0),l->y+(l->kind==3?j:0),l->kind==4?1:l->w,l->kind==3?1:l->h);
                    }
                }
            }
        }
    } else {
        for(int y=0;y<FF_ROWS;++y) for(int x=0;x<FF_COLS;++x) if(a->tiles[y][x]) {
            color(app,70,103,127);rect(app,x*16,y*16,16,a->tiles[y][x]==FF_PLATFORM?6:16);
            color(app,205,237,247);rect(app,x*16,y*16,16,3);
        }
    }
}
static int animation_image(const FF_Arena *a,int player,int part,int anim,int direction,uint32_t tick) {
    const FF_Sequence *s=&a->sprites[player][part][anim][direction];
    if(!s->count) s=&a->sprites[player][part][1][direction];
    if(!s->count) s=&a->sprites[player][part][0][direction];
    if(!s->count) s=&a->sprites[player][part][0][0];
    if(!s->count) return -1;
    return s->image[(tick/4)%(uint32_t)s->count];
}
static void draw_player(App *app,const FF_Arena *a,const FF_Game *g,int i) {
    const FF_Player *p=&g->players[i];if(p->respawn||(p->invulnerable&&g->tick%4<2)) return;
    int x=p->x/FF_FP,y=p->y/FF_FP,dir=p->facing<0;
    int anim=p->grounded?(abs(p->vx)>FF_FP/4?1:0):(p->vy<0?7:8);
    if(a->imported) {
        /* The source uses independent feet/body/hand/hat objects at one origin. */
        const int order[]={0,1,2,3,4};
        for(int part=0;part<FF_PARTS;++part) {
            int index=order[part];int active_anim=index==2&&p->punch_ticks?12:anim;
            if(index==4&&p->weapon==FF_FISTS) continue;
            if(index==4) active_anim=p->weapon==FF_ICE?13:p->weapon==FF_ROCKET?14:15;
            sprite(app,a,animation_image(a,i,index,active_anim,dir,g->tick),x,y-16);
        }
    } else {
        color(app,i?234:70,i?83:157,i?74:243);rect(app,x-12,y-31,24,26);
        color(app,240,245,255);rect(app,x-13,y-31,26,4);
        color(app,30,38,57);rect(app,x+(dir?-8:4),y-21,4,4);
        color(app,i?255:80,i?110:170,i?100:250);
        rect(app,x-14,y-5,11,5);rect(app,x+3,y-5,11,5);
        if(p->punch_ticks) rect(app,x+(dir?-30:12),y-22,18,10);
    }
    if(p->frozen) {color(app,150,240,255);SDL_Rect r={x-14,y-34,28,34};SDL_RenderDrawRect(app->renderer,&r);}
}
static void hud(App *app,const FF_Game *g) {
    color(app,12,20,33);rect(app,0,560,800,40);
    const char *weapons[]={"FISTS","ICE","FLAME","ROCKET"};char s[120];
    for(int i=0;i<2;++i) {
        const FF_Player *p=&g->players[i];int x=i?426:16;
        color(app,i?250:90,i?100:170,i?94:255);
        snprintf(s,sizeof(s),"%s  LIVES %d  WINS %d",i?"RED":"BLUE",p->lives,p->score);text(app,x,564,1,s);
        color(app,45,54,66);rect(app,x,575,350,8);
        color(app,i?240:55,i?65:155,i?75:250);rect(app,x,575,p->health*350/100,8);
        color(app,225,233,242);snprintf(s,sizeof(s),"%s %d  HP %d",weapons[p->weapon],p->ammo,p->health);text(app,x,590,1,s);
        color(app,220,194,75);rect(app,x+195,590,p->fuel/2,5);
    }

}
static void draw(App *app,const FF_Arena *a,const FF_Game *g,bool help,bool paused) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];FF_Point pos=ff_device_position(d,g->tick);
        Image *im=load_image(app,d->image);
        if(im) {SDL_Rect dest={pos.x,pos.y,im->w,im->h};SDL_RenderCopy(app->renderer,im->texture,NULL,&dest);}
    }
    for(int i=0;i<FF_PICKUPS;++i) {const FF_Pickup *p=&g->pickups[i];if(!p->active) continue;
        int id=a->pickup_images[p->kind];
        if(id>=0) sprite(app,a,id,p->x,p->y);
        else {color(app,220,190,70);rect(app,p->x-9,p->y-9,18,18);color(app,20,30,40);
            const char *names[]={"","I","F","R","H","J"};text(app,p->x-5,p->y-5,2,names[p->kind]);}
    }
    for(int i=0;i<2;++i) draw_player(app,a,g,i);
    for(int i=0;i<FF_SHOTS;++i) {const FF_Shot *s=&g->shots[i];if(!s->life) continue;
        int id=a->shot_images[s->kind];
        if(id>=0) {
            Image *im=load_image(app,id);
            if(im) {
                bool left=s->vx<0;int anchor=left?im->w-1-a->hot_x[id]:a->hot_x[id];
                SDL_Rect dest={s->x/FF_FP-anchor,s->y/FF_FP-a->hot_y[id],im->w,im->h};
                SDL_RenderCopyEx(app->renderer,im->texture,NULL,&dest,0,NULL,left?SDL_FLIP_HORIZONTAL:SDL_FLIP_NONE);
            }
        }
        else {color(app,s->kind==FF_ICE?150:255,s->kind==FF_ICE?230:130,80);rect(app,s->x/FF_FP-4,s->y/FF_FP-3,8,6);}
    }
    hud(app,g);
    if(help||paused||g->winner>=0) {
        color(app,12,20,33);rect(app,90,160,620,270);color(app,232,242,250);
        if(help) {
            text(app,140,182,3,"FUNNY FURRIES PROTOTYPE");
            text(app,125,218,2,"RED   F H MOVE  T JUMP  Z PUNCH");
            text(app,125,240,2,"      A FIRE  Q JETPACK");
            text(app,125,270,2,"BLUE  ARROWS  CTRL PUNCH");
            text(app,125,292,2,"      SHIFT FIRE  / JETPACK");
            text(app,125,324,2,"PAD   STICK MOVE  A JUMP  X PUNCH");
            text(app,125,346,2,"      B/RT FIRE  Y/LT JETPACK");
            text(app,125,382,2,"3 LIVES PER MATCH  F1 TO PLAY");
        } else if(paused) text(app,240,270,4,"PAUSED - P TO PLAY");
        else {text(app,225,252,4,g->winner==2?"DRAW":g->winner==0?"BLUE WINS":"RED WINS");text(app,210,302,2,"NEXT ROUND STARTS SHORTLY");}
    }
}
static bool assets_ready(App *app,const FF_Arena *a) {
    for(int i=0;i<a->layer_count;++i) if(a->layers[i].image>=0&&!load_image(app,a->layers[i].image)) return false;
    for(int p=0;p<2;++p) for(int part=0;part<FF_PARTS;++part) for(int k=0;k<FF_ANIMS;++k) for(int d=0;d<2;++d) {
        const FF_Sequence *s=&a->sprites[p][part][k][d];
        for(int i=0;i<s->count;++i) if(!load_image(app,s->image[i])) return false;
    }
    for(int i=0;i<a->device_count;++i) if(!load_image(app,a->devices[i].image)) return false;
    for(int i=1;i<6;++i) if(a->pickup_images[i]>=0&&!load_image(app,a->pickup_images[i])) return false;
    for(int i=1;i<4;++i) if(a->shot_images[i]>=0&&!load_image(app,a->shot_images[i])) return false;
    return true;
}
static bool parse_ticks(const char *s,int *ticks) {
    char *end;errno=0;long value=strtol(s,&end,10);
    if(errno||*end||value<1||value>10000000) return false;
    *ticks=(int)value;return true;
}
int main(int argc,char **argv) {
    const char *data=NULL,*screenshot=NULL;int ticks=0;bool auto_play=false;
    for(int i=1;i<argc;++i) {
        if(!strcmp(argv[i],"--data")&&i+1<argc) data=argv[++i];
        else if(!strcmp(argv[i],"--smoke")&&i+1<argc&&parse_ticks(argv[i+1],&ticks)) {++i;auto_play=true;}
        else if(!strcmp(argv[i],"--screenshot")&&i+1<argc) screenshot=argv[++i];
        else if(!strcmp(argv[i],"--help")) {puts("funny-furries [--data LOCAL_IMPORT] [--smoke TICKS] [--screenshot FILE.bmp]\nWithout --data, play the asset-free practice arena. F1 shows controls.");return 0;}
        else {fprintf(stderr,"Unknown or incomplete option. Use --help.\n");return 2;}
    }
    ff_fault_init();
    static FF_Arena arena;FF_Game game;App app={0};int result=1;char error[256];
    if(data) {
        char path[4096];if(snprintf(path,sizeof(path),"%s/arena.ff",data)>=(int)sizeof(path)||!ff_arena_load(&arena,path,error,sizeof(error))) {
            fprintf(stderr,"Cannot load local import. Run tools/import_arena.py first.\n");return 2;
        }
        app.assets=data;
    } else ff_arena_practice(&arena);
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER|SDL_INIT_AUDIO)<0) goto fail;
    if(!(IMG_Init(IMG_INIT_PNG)&IMG_INIT_PNG)) goto fail;
    app.window=SDL_CreateWindow("Funny Furries - development prototype",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,1000,750,SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI);
    if(!app.window) goto fail;
    app.renderer=SDL_CreateRenderer(app.window,-1,SDL_RENDERER_ACCELERATED|SDL_RENDERER_PRESENTVSYNC);
    if(!app.renderer) app.renderer=SDL_CreateRenderer(app.window,-1,SDL_RENDERER_SOFTWARE);
    if(!app.renderer||SDL_RenderSetLogicalSize(app.renderer,FF_W,FF_H)<0) goto fail;
    app.scene=SDL_CreateTexture(app.renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,FF_W,FF_H);
    if(!app.scene) goto fail;
    if(data&&!assets_ready(&app,&arena)) {fprintf(stderr,"Incomplete local image import.\n");result=2;goto cleanup;}
    app.backdrop=SDL_CreateTexture(app.renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,FF_W,FF_H);
    if(!app.backdrop||SDL_SetRenderTarget(app.renderer,app.backdrop)<0) goto fail;
    background(&app,&arena);
    if(SDL_SetRenderTarget(app.renderer,NULL)<0) goto fail;
    app.audio=Mix_OpenAudio(44100,AUDIO_S16SYS,2,1024)==0;
    if(app.audio&&data) for(int i=0;i<7;++i) if(arena.sound_ids[i]>=0) {
        char path[4096];snprintf(path,sizeof(path),"%s/sound-23-%d.wav",data,arena.sound_ids[i]);
        app.sounds[i]=Mix_LoadWAV(path);
        if(!app.sounds[i]) {fprintf(stderr,"Incomplete local sound import.\n");result=2;goto cleanup;}
        Mix_VolumeChunk(app.sounds[i],MIX_MAX_VOLUME/3);
    }
    ff_input_init(&app.input);ff_game_init(&game,&arena,12345);
    bool running=true,help=!auto_play,paused=false;uint64_t previous=SDL_GetPerformanceCounter(),accumulator=0;
    uint64_t frequency=SDL_GetPerformanceFrequency();
    while(running) {
        SDL_Event event;
        while(SDL_PollEvent(&event)) {
            ff_input_event(&app.input,&event);
            if(event.type==SDL_QUIT) running=false;
            if(event.type==SDL_WINDOWEVENT&&event.window.event==SDL_WINDOWEVENT_FOCUS_LOST&&!auto_play) paused=true;
            if(event.type==SDL_KEYDOWN&&!event.key.repeat) {
                if(event.key.keysym.sym==SDLK_ESCAPE) running=false;
                if(event.key.keysym.sym==SDLK_F1) help=!help;
                if(event.key.keysym.sym==SDLK_p) paused=!paused;
                if(event.key.keysym.sym==SDLK_r) {ff_game_init(&game,&arena,12345);paused=false;help=false;}
            }
            if(event.type==SDL_CONTROLLERBUTTONDOWN) {
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_START) {if(help) help=false;else paused=!paused;}
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK&&game.winner>=0) ff_game_init(&game,&arena,12345);
            }
        }
        uint64_t now=SDL_GetPerformanceCounter(),elapsed=now-previous;previous=now;
        if(elapsed>frequency/4) elapsed=frequency/4;
        accumulator+=elapsed*FF_HZ;
        if(auto_play) accumulator=frequency;
        if(paused||help) accumulator=0;
        while(accumulator>=frequency) {
            uint8_t keys[2];ff_input_read(&app.input,keys);
            if(auto_play) {keys[0]=(game.tick%200<100?FF_RIGHT:FF_LEFT)|(game.tick%33==0?FF_JUMP:0)|FF_FIRE|(game.tick%20==0?FF_PUNCH:0);keys[1]=(game.tick%180<90?FF_LEFT:FF_RIGHT)|(game.tick%47==0?FF_JUMP:0)|FF_FIRE|(game.tick%21==0?FF_PUNCH:0);}
            ff_game_tick(&game,&arena,keys);accumulator-=frequency;
            if(app.audio) for(int i=0;i<7;++i) if((game.sounds&(1u<<i))&&app.sounds[i]) Mix_PlayChannel(-1,app.sounds[i],0);
            if(auto_play&&game.tick>=(uint32_t)ticks) {running=false;break;}
        }
        if(SDL_SetRenderTarget(app.renderer,app.scene)<0) goto fail;
        draw(&app,&arena,&game,help,paused);
        if(SDL_SetRenderTarget(app.renderer,NULL)<0) goto fail;
        color(&app,0,0,0);SDL_RenderClear(app.renderer);
        if(SDL_RenderCopy(app.renderer,app.scene,NULL,NULL)<0) goto fail;
        if(!running&&screenshot) {
            int w,h;SDL_GetRendererOutputSize(app.renderer,&w,&h);
            SDL_Surface *s=SDL_CreateRGBSurfaceWithFormat(0,w,h,32,SDL_PIXELFORMAT_RGBA32);
            if(!s||SDL_RenderReadPixels(app.renderer,NULL,SDL_PIXELFORMAT_RGBA32,s->pixels,s->pitch)<0||SDL_SaveBMP(s,screenshot)<0) {SDL_FreeSurface(s);goto fail;}
            SDL_FreeSurface(s);
        }
        SDL_RenderPresent(app.renderer);
        if(!auto_play) SDL_Delay(1);
    }
    printf("ticks=%u state=%08x arena=%s\n",game.tick,ff_game_hash(&game),arena.imported?"local-import":"practice");
    result=0;goto cleanup;
fail:
    fprintf(stderr,"Runtime fault: %s\n",SDL_GetError());ff_fault("runtime");
cleanup:
    ff_input_close(&app.input);
    for(int i=0;i<FF_IMAGES;++i) if(app.images[i].texture) SDL_DestroyTexture(app.images[i].texture);
    for(int i=0;i<7;++i) if(app.sounds[i]) Mix_FreeChunk(app.sounds[i]);
    if(app.audio) Mix_CloseAudio();
    if(app.scene) SDL_DestroyTexture(app.scene);
    if(app.backdrop) SDL_DestroyTexture(app.backdrop);
    if(app.renderer) SDL_DestroyRenderer(app.renderer);
    if(app.window) SDL_DestroyWindow(app.window);
    IMG_Quit();SDL_Quit();return result;
}
