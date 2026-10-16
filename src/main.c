#include "game.h"
#include "input.h"
#include "fault.h"
#include <SDL_image.h>
#include <SDL_mixer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <math.h>

typedef struct { SDL_Texture *texture; int w,h; } Image;
typedef struct {
    SDL_Window *window;SDL_Renderer *renderer;SDL_Texture *scene,*backdrop; FF_Input input;
    Image images[FF_IMAGES], tinted[2][FF_IMAGES]; Mix_Chunk *sounds[FF_SOUNDS]; bool audio;
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
static void centered(App *app,int y,int scale,const char *s) {text(app,(FF_W-(int)strlen(s)*6*scale)/2,y,scale,s);}
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
/* Seats 3 and 4 reuse the blue and red furry with the body hue turned to
 * green and yellow, computed from the player's own art at load time. */
static Image *load_tinted(App *app,int id,int seat) {
    if(seat<2) return load_image(app,id);
    if(id<0||id>=FF_IMAGES||!app->assets) return NULL;
    Image *image=&app->tinted[seat-2][id];
    if(image->texture) return image;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/image-21-%d.png",app->assets,id)>=(int)sizeof(path)) return NULL;
    SDL_Surface *loaded=IMG_Load(path);if(!loaded) return NULL;
    SDL_Surface *s=SDL_ConvertSurfaceFormat(loaded,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(loaded);
    if(!s) return NULL;
    double shift=seat==2?-100.0:65.0;
    if(SDL_LockSurface(s)==0) {
        for(int y=0;y<s->h;++y) {
            Uint8 *row=(Uint8 *)s->pixels+y*s->pitch;
            for(int x=0;x<s->w;++x) {
                Uint8 *px=row+4*x;double r=px[0]/255.0,g=px[1]/255.0,b=px[2]/255.0;
                double max=fmax(r,fmax(g,b)),min=fmin(r,fmin(g,b)),delta=max-min;
                if(max<=0||delta/max<0.25) continue;
                double h=max==r?fmod((g-b)/delta,6.0):max==g?(b-r)/delta+2:(r-g)/delta+4;
                h=fmod(h*60.0+shift+720.0,360.0)/60.0;
                double c=delta,xx=c*(1-fabs(fmod(h,2.0)-1)),rr=0,gg=0,bb=0;
                if(h<1){rr=c;gg=xx;}else if(h<2){rr=xx;gg=c;}else if(h<3){gg=c;bb=xx;}
                else if(h<4){gg=xx;bb=c;}else if(h<5){rr=xx;bb=c;}else{rr=c;bb=xx;}
                px[0]=(Uint8)lround((rr+min)*255);px[1]=(Uint8)lround((gg+min)*255);px[2]=(Uint8)lround((bb+min)*255);
            }
        }
        SDL_UnlockSurface(s);
    }
    image->w=s->w;image->h=s->h;image->texture=SDL_CreateTextureFromSurface(app->renderer,s);SDL_FreeSurface(s);
    return image->texture?image:load_image(app,id);
}
static void sprite_for(App *app,const FF_Arena *a,int id,int x,int y,int seat) {
    Image *image=load_tinted(app,id,seat);if(!image) return;
    SDL_Rect dest={x-a->hot_x[id],y-a->hot_y[id],image->w,image->h};
    SDL_RenderCopy(app->renderer,image->texture,NULL,&dest);
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
static const char *const seat_name[FF_PLAYERS]={"BLUE","RED","GREEN","YELLOW"};
static const int seat_color[FF_PLAYERS][3]={{90,170,255},{250,100,94},{110,225,95},{245,215,60}};
static const int seat_body[FF_PLAYERS][3]={{55,155,250},{240,65,75},{60,190,70},{230,190,30}};
static int animation_image(const FF_Arena *a,int player,int part,int anim,int direction,uint32_t tick) {
    player&=1;
    const FF_Sequence *s=&a->sprites[player][part][anim][direction];
    if(!s->count) s=&a->sprites[player][part][1][direction];
    if(!s->count) s=&a->sprites[player][part][0][direction];
    if(!s->count) s=&a->sprites[player][part][0][0];
    if(!s->count) return -1;
    return s->image[(tick/4)%(uint32_t)s->count];
}
static void draw_player(App *app,const FF_Arena *a,const FF_Game *g,int i) {
    const FF_Player *p=&g->players[i];if(!p->active||!p->lives||p->respawn||(p->invulnerable&&g->tick%4<2)) return;
    int x=p->x/FF_FP,y=p->y/FF_FP,dir=p->facing<0;
    int anim=p->grounded?(abs(p->vx)>FF_FP/4?1:0):(p->vy<0?7:8);
    if(a->imported) {
        /* The source uses independent feet/body/hand/hat objects at one origin. */
        const int order[]={0,1,2,3,4};
        for(int part=0;part<FF_PARTS;++part) {
            int index=order[part];int active_anim=index==2&&p->punch_ticks?12:anim;
            if(index==4&&p->weapon==FF_FISTS) continue;
            if(index==4) active_anim=p->weapon==FF_ICE?13:p->weapon==FF_ROCKET?14:15;
            int id=animation_image(a,i,index,active_anim,dir,g->tick);
            if(index==1) sprite_for(app,a,id,x,y-16,i);else sprite(app,a,id,x,y-16);
        }
    } else {
        color(app,seat_body[i][0],seat_body[i][1],seat_body[i][2]);rect(app,x-12,y-31,24,26);
        color(app,240,245,255);rect(app,x-13,y-31,26,4);
        color(app,30,38,57);rect(app,x+(dir?-8:4),y-21,4,4);
        color(app,seat_color[i][0],seat_color[i][1],seat_color[i][2]);
        rect(app,x-14,y-5,11,5);rect(app,x+3,y-5,11,5);
        if(p->punch_ticks) rect(app,x+(dir?-30:12),y-22,18,10);
    }
}
static void hud(App *app,const FF_Game *g) {
    color(app,12,20,33);rect(app,0,560,800,40);
    const char *weapons[]={"FISTS","ICE","FLAME","ROCKET"};char s[120];
    int seats=0;for(int i=0;i<FF_PLAYERS;++i) seats+=g->players[i].active;
    if(!seats) return;
    int field=FF_W/seats,slot=0;bool wide=seats<=2;
    for(int i=0;i<FF_PLAYERS;++i) {
        const FF_Player *p=&g->players[i];if(!p->active) continue;
        int x=slot++*field+(wide?16:10),bar=field-(wide?50:20);
        color(app,seat_color[i][0],seat_color[i][1],seat_color[i][2]);
        if(wide) snprintf(s,sizeof(s),"%s  LIVES %d  WINS %d",seat_name[i],p->lives,p->score);
        else snprintf(s,sizeof(s),"%s L%d W%d",seat_name[i],p->lives,p->score);
        text(app,x,564,1,s);
        color(app,45,54,66);rect(app,x,575,bar,8);
        if(p->lives) {color(app,seat_body[i][0],seat_body[i][1],seat_body[i][2]);rect(app,x,575,p->health*bar/100,8);}
        color(app,225,233,242);
        if(!p->lives) snprintf(s,sizeof(s),"OUT");
        else if(wide) snprintf(s,sizeof(s),"%s %d  HP %d",weapons[p->weapon],p->ammo,p->health);
        else snprintf(s,sizeof(s),"%s %d",weapons[p->weapon],p->ammo);
        text(app,x,590,1,s);
        if(p->lives) {color(app,220,194,75);rect(app,x+(wide?195:bar-75),590,p->fuel/(wide?2:4),5);}
    }
}
static void draw_help(App *app);
static void draw(App *app,const FF_Arena *a,const FF_Game *g,bool help,bool paused) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];FF_Point pos=ff_device_position(a,i,g->tick);
        Image *im=load_image(app,d->image);
        if(im) {SDL_Rect dest={pos.x,pos.y,im->w,im->h};SDL_RenderCopy(app->renderer,im->texture,NULL,&dest);}
    }
    for(int i=0;i<FF_HAZARDS;++i) {
        const FF_Hazard *h=&g->hazards[i];if(!h->life) continue;
        const FF_Sequence *seq=&a->hazard_sprites[h->kind-1][h->vx<0];
        if(!seq->count) seq=&a->hazard_sprites[h->kind-1][0];
        int x=h->x/FF_FP,y=h->y/FF_FP;
        if(seq->count) sprite(app,a,seq->image[(g->tick/4)%(unsigned)seq->count],x,y);
        else {color(app,245,80,35);rect(app,x-6,y-6,12,12);color(app,255,220,90);rect(app,x-2,y-10,4,5);}
    }
    for(int i=0;i<FF_PICKUPS;++i) {const FF_Pickup *p=&g->pickups[i];if(!p->active) continue;
        int id=a->pickup_images[p->kind];
        if(id>=0) sprite(app,a,id,p->x,p->y);
        else {color(app,220,190,70);rect(app,p->x-9,p->y-9,18,18);color(app,20,30,40);
            const char *names[]={"","I","F","R","H","J"};text(app,p->x-5,p->y-5,2,names[p->kind]);}
    }
    for(int i=0;i<FF_PLAYERS;++i) draw_player(app,a,g,i);
    for(int i=0;i<FF_SHOTS;++i) {const FF_Shot *s=&g->shots[i];if(!s->life) continue;
        const FF_Sequence *fire=&a->fire_sprites[s->life<=20];
        if(s->kind==FF_FLAME&&fire->count) {
            int frame=s->life<=20?(20-s->life)*fire->count/20:(270-s->life)/4%fire->count;
            sprite(app,a,fire->image[frame],s->x/FF_FP,s->y/FF_FP);continue;
        }
        if(s->kind==FF_FLAME&&s->life<=20&&s->life%4<2) continue;
        int id=a->shot_images[s->kind];
        if(id>=0) {
            Image *im=load_image(app,id);
            if(im) {
                if(s->kind==FF_ROCKET) {
                    SDL_Point origin={a->hot_x[id],a->hot_y[id]};
                    SDL_Rect dest={s->x/FF_FP-origin.x,s->y/FF_FP-origin.y,im->w,im->h};
                    SDL_RenderCopyEx(app->renderer,im->texture,NULL,&dest,-s->direction*11.25,&origin,SDL_FLIP_NONE);
                } else {
                    bool left=s->vx<0;int anchor=left?im->w-1-a->hot_x[id]:a->hot_x[id];
                    SDL_Rect dest={s->x/FF_FP-anchor,s->y/FF_FP-a->hot_y[id],im->w,im->h};
                    SDL_RenderCopyEx(app->renderer,im->texture,NULL,&dest,0,NULL,left?SDL_FLIP_HORIZONTAL:SDL_FLIP_NONE);
                }
            }
        }
        else {color(app,s->kind==FF_ICE?150:255,s->kind==FF_ICE?230:130,80);rect(app,s->x/FF_FP-4,s->y/FF_FP-3,8,6);}
    }
    for(int i=0;i<FF_BLASTS;++i) {
        const FF_Blast *b=&g->blasts[i];if(!b->life) continue;
        int x=b->x/FF_FP,y=b->y/FF_FP;
        if(a->blast_sprite.count) {
            int frame=(20-b->life)*a->blast_sprite.count/20;
            sprite(app,a,a->blast_sprite.image[frame],x,y);
        } else {
            int r=10+b->life;color(app,255,130,35);rect(app,x-r,y-r,r*2,r*2);
            color(app,255,225,100);rect(app,x-r/2,y-r/2,r,r);
        }
    }
    hud(app,g);
    if(help||paused||g->winner>=0) {
        color(app,12,20,33);rect(app,90,160,620,270);color(app,232,242,250);
        if(help) draw_help(app);
        else if(paused) text(app,240,270,4,"PAUSED - P TO PLAY");
        else {
            char s[64];
            if(g->winner==FF_DRAW) snprintf(s,sizeof(s),"DRAW");
            else if(g->winner>=FF_TEAM_WIN) snprintf(s,sizeof(s),"TEAM %s WINS",g->winner==FF_TEAM_WIN?"BLUE":"RED");
            else snprintf(s,sizeof(s),"%s WINS",seat_name[g->winner]);
            centered(app,252,4,s);centered(app,302,2,"NEXT ROUND STARTS SHORTLY");
        }
    }
}
static void draw_help(App *app) {
            color(app,12,20,33);rect(app,90,160,620,270);color(app,232,242,250);
            text(app,140,182,3,"FUNNY FURRIES CONTROLS");
            text(app,125,218,2,"RED   F H MOVE  T JUMP  Z PUNCH");
            text(app,125,240,2,"      A FIRE  Q JETPACK");
            text(app,125,270,2,"BLUE  ARROWS  CTRL PUNCH");
            text(app,125,292,2,"      SHIFT FIRE  / JETPACK");
            text(app,125,324,2,"PAD   STICK MOVE  A JUMP  X PUNCH");
            text(app,125,346,2,"      B/RT FIRE  Y/LT JETPACK");
            text(app,125,382,2,"ESC/BACK MENU  F1 CLOSE");
}
typedef struct { unsigned joined; int mode; uint8_t previous[FF_PLAYERS]; } Lobby;
static bool seat_usable(const FF_Input *in,int seat) {return seat<2||ff_input_has_pad(in,seat);}
static int seat_count(unsigned joined) {int n=0;for(int i=0;i<FF_PLAYERS;++i) n+=!!(joined&(1u<<i));return n;}
static bool lobby_ready(const Lobby *l) {
    int n=seat_count(l->joined);return l->mode==FF_TEAMS?n==4:n>=2;
}
/* Jump joins a seat, fire leaves it and jetpack switches the mode; every seat
 * uses the controls it plays with, so nobody needs to learn menu buttons. */
static void lobby_update(Lobby *l,const FF_Input *in,const uint8_t keys[FF_PLAYERS]) {
    for(int i=0;i<FF_PLAYERS;++i) {
        uint8_t pressed=keys[i]&(uint8_t)~l->previous[i];l->previous[i]=keys[i];
        if(!seat_usable(in,i)) {l->joined&=~(1u<<i);continue;}
        if(pressed&FF_JUMP) l->joined|=1u<<i;
        if(pressed&FF_FIRE) l->joined&=~(1u<<i);
        if((pressed&FF_FLY)&&(l->joined&(1u<<i))) l->mode=l->mode==FF_TEAMS?FF_FFA:FF_TEAMS;
    }
}
static void draw_lobby(App *app,const Lobby *l,const FF_Input *in) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    color(app,12,20,33);rect(app,30,60,740,480);
    color(app,232,242,250);centered(app,90,4,"FUNNY FURRIES");
    centered(app,135,1,"UP TO FOUR PLAYERS ON ONE SCREEN");
    for(int i=0;i<FF_PLAYERS;++i) {
        int x=55+i*180;bool joined=l->joined&(1u<<i),usable=seat_usable(in,i);
        color(app,joined?seat_body[i][0]/3:30,joined?seat_body[i][1]/3:38,joined?seat_body[i][2]/3:50);rect(app,x,170,150,170);
        color(app,seat_color[i][0],seat_color[i][1],seat_color[i][2]);rect(app,x,170,150,6);
        char s[32];snprintf(s,sizeof(s),"PLAYER %d",i+1);text(app,x+12,190,2,s);
        text(app,x+12,215,2,seat_name[i]);
        if(l->mode==FF_TEAMS) {color(app,200,210,220);text(app,x+12,240,1,i&1?"TEAM RED":"TEAM BLUE");}
        color(app,170,185,200);
        const char *device=ff_input_has_pad(in,i)?(i==0?"PAD OR ARROWS":i==1?"PAD OR F T H":"PAD"):i==0?"KEYS ARROWS":i==1?"KEYS F T H":"CONNECT A PAD";
        text(app,x+12,260,1,device);
        color(app,232,242,250);
        if(joined) text(app,x+12,295,3,"READY");
        else if(usable) {text(app,x+12,290,2,"PRESS A");text(app,x+12,312,1,i==0?"OR UP TO JOIN":i==1?"OR T TO JOIN":"TO JOIN");}
    }
    color(app,232,242,250);
    centered(app,370,2,l->mode==FF_TEAMS?"MODE: 2 VS 2":"MODE: FREE FOR ALL");
    color(app,170,185,200);
    centered(app,400,1,"A/JUMP JOIN   B/FIRE LEAVE   Y/JETPACK CHANGE MODE");
    int n=seat_count(l->joined);
    color(app,232,242,250);
    if(lobby_ready(l)) centered(app,440,3,"START OR ENTER TO PLAY");
    else if(l->mode==FF_TEAMS) centered(app,440,2,"2 VS 2 NEEDS FOUR PLAYERS");
    else centered(app,440,2,n?"ONE MORE PLAYER NEEDED":"TWO PLAYERS NEEDED");
    color(app,170,185,200);centered(app,500,1,"F1 CONTROLS   ESC QUIT");
}
static unsigned seats_of(const FF_Game *g) {
    unsigned seats=0;for(int i=0;i<FF_PLAYERS;++i) if(g->players[i].active) seats|=1u<<i;
    return seats;
}
static bool assets_ready(App *app,const FF_Arena *a) {
    for(int i=0;i<a->layer_count;++i) if(a->layers[i].image>=0&&!load_image(app,a->layers[i].image)) return false;
    for(int p=0;p<2;++p) for(int part=0;part<FF_PARTS;++part) for(int k=0;k<FF_ANIMS;++k) for(int d=0;d<2;++d) {
        const FF_Sequence *s=&a->sprites[p][part][k][d];
        for(int i=0;i<s->count;++i) if(!load_image(app,s->image[i])) return false;
    }
    for(int h=0;h<3;++h) for(int d=0;d<2;++d) {
        const FF_Sequence *s=&a->hazard_sprites[h][d];
        for(int i=0;i<s->count;++i) if(!load_image(app,s->image[i])) return false;
    }
    for(int i=0;i<a->blast_sprite.count;++i) if(!load_image(app,a->blast_sprite.image[i])) return false;
    for(int k=0;k<2;++k) for(int i=0;i<a->fire_sprites[k].count;++i)
        if(!load_image(app,a->fire_sprites[k].image[i])) return false;
    for(int i=0;i<a->device_count;++i) if(a->devices[i].image>=0&&!load_image(app,a->devices[i].image)) return false;
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
    const char *data=NULL,*screenshot=NULL;int ticks=0,players=2;bool auto_play=false,fullscreen=false,teams=false,show_lobby=false;
    for(int i=1;i<argc;++i) {
        if(!strcmp(argv[i],"--fullscreen")) fullscreen=true;
        else if(!strcmp(argv[i],"--data")&&i+1<argc) data=argv[++i];
        else if(!strcmp(argv[i],"--smoke")&&i+1<argc&&parse_ticks(argv[i+1],&ticks)) {++i;auto_play=true;}
        else if(!strcmp(argv[i],"--screenshot")&&i+1<argc) screenshot=argv[++i];
        else if(!strcmp(argv[i],"--players")&&i+1<argc&&argv[i+1][0]>='2'&&argv[i+1][0]<='4'&&!argv[i+1][1]) players=argv[++i][0]-'0';
        else if(!strcmp(argv[i],"--teams")) teams=true;
        else if(!strcmp(argv[i],"--lobby")) show_lobby=true;
        else if(!strcmp(argv[i],"--help")) {puts("funny-furries [--fullscreen] [--data LOCAL_IMPORT] [--smoke TICKS [--players 2-4] [--teams] [--lobby]] [--screenshot FILE.bmp]\nWithout --data, play the asset-free practice arena. F1 shows controls.");return 0;}
        else {fprintf(stderr,"Unknown or incomplete option. Use --help.\n");return 2;}
    }
    if(teams&&players!=4) {fprintf(stderr,"--teams needs --players 4.\n");return 2;}
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
    app.window=SDL_CreateWindow("Funny Furries 0.2.0 - test release",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,1000,750,SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI|(fullscreen?SDL_WINDOW_FULLSCREEN_DESKTOP:0));
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
    if(app.audio&&data) for(int i=0;i<FF_SOUNDS;++i) if(arena.sound_ids[i]>=0) {
        char path[4096];snprintf(path,sizeof(path),"%s/sound-23-%d.wav",data,arena.sound_ids[i]);
        app.sounds[i]=Mix_LoadWAV(path);
        if(!app.sounds[i]) {fprintf(stderr,"Incomplete local sound import.\n");result=2;goto cleanup;}
        Mix_VolumeChunk(app.sounds[i],MIX_MAX_VOLUME/3);
    }
    ff_input_init(&app.input);
    ff_game_setup(&game,&arena,12345,(1u<<players)-1,teams?FF_TEAMS:FF_FFA);
    Lobby lobby={0};
    bool running=true,help=false,paused=false,in_lobby=!auto_play||show_lobby;uint64_t previous=SDL_GetPerformanceCounter(),accumulator=0;
    uint64_t frequency=SDL_GetPerformanceFrequency();
    while(running) {
        SDL_Event event;bool start=false,back=false;
        while(SDL_PollEvent(&event)) {
            ff_input_event(&app.input,&event);
            if(event.type==SDL_QUIT) running=false;
            if(event.type==SDL_WINDOWEVENT&&event.window.event==SDL_WINDOWEVENT_FOCUS_LOST&&!auto_play) paused=true;
            if(event.type==SDL_KEYDOWN&&!event.key.repeat) {
                SDL_Keycode key=event.key.keysym.sym;
                if(key==SDLK_F1) help=!help;
                else if(in_lobby) {
                    if(key==SDLK_ESCAPE) running=false;
                    if((key==SDLK_RETURN||key==SDLK_KP_ENTER)&&lobby_ready(&lobby)) start=true;
                } else {
                    if(key==SDLK_ESCAPE) back=true;
                    if(key==SDLK_p) paused=!paused;
                    if(key==SDLK_r) {ff_game_setup(&game,&arena,game.rng,seats_of(&game),game.mode);paused=false;help=false;}
                }
            }
            if(event.type==SDL_CONTROLLERBUTTONDOWN) {
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_START) {
                    if(help) help=false;
                    else if(in_lobby) start=lobby_ready(&lobby);
                    else paused=!paused;
                }
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK) {if(help) help=false;else if(!in_lobby) back=true;}
            }
        }
        if(in_lobby&&!auto_play) {
            uint8_t keys[FF_PLAYERS];ff_input_read(&app.input,keys);
            if(!help) lobby_update(&lobby,&app.input,keys);
            if(start&&lobby_ready(&lobby)) {
                ff_game_setup(&game,&arena,(uint32_t)SDL_GetPerformanceCounter()|1u,lobby.joined,lobby.mode);
                in_lobby=paused=false;
            }
        } else if(back) {in_lobby=true;paused=false;ff_input_read(&app.input,lobby.previous);}
        uint64_t now=SDL_GetPerformanceCounter(),elapsed=now-previous;previous=now;
        if(elapsed>frequency/4) elapsed=frequency/4;
        accumulator+=elapsed*FF_HZ;
        if(auto_play) accumulator=frequency;
        if(paused||help||(in_lobby&&!auto_play)) accumulator=0;
        while(accumulator>=frequency) {
            uint8_t keys[FF_PLAYERS];ff_input_read(&app.input,keys);
            if(auto_play) {
                keys[0]=(game.tick%200<100?FF_RIGHT:FF_LEFT)|(game.tick%33==0?FF_JUMP:0)|FF_FIRE|(game.tick%20==0?FF_PUNCH:0);keys[1]=(game.tick%180<90?FF_LEFT:FF_RIGHT)|(game.tick%47==0?FF_JUMP:0)|FF_FIRE|(game.tick%21==0?FF_PUNCH:0);
                keys[2]=(game.tick%160<80?FF_RIGHT:FF_LEFT)|(game.tick%29==0?FF_JUMP:0)|FF_FIRE|(game.tick%23==0?FF_PUNCH:0);keys[3]=(game.tick%220<110?FF_LEFT:FF_RIGHT)|(game.tick%41==0?FF_JUMP:0)|FF_FIRE|(game.tick%19==0?FF_PUNCH:0);
                if(show_lobby) {lobby_update(&lobby,&app.input,keys);memset(keys,0,sizeof(keys));++game.tick;}
            }
            if(!in_lobby) ff_game_tick(&game,&arena,keys);
            accumulator-=frequency;
            if(app.audio) for(int i=0;i<FF_SOUNDS;++i) if((game.sounds&(1u<<i))&&app.sounds[i]) Mix_PlayChannel(-1,app.sounds[i],0);
            if(auto_play&&game.tick>=(uint32_t)ticks) {running=false;break;}
        }
        if(SDL_SetRenderTarget(app.renderer,app.scene)<0) goto fail;
        if(in_lobby) {draw_lobby(&app,&lobby,&app.input);if(help) draw_help(&app);}
        else draw(&app,&arena,&game,help,paused);
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
    for(int i=0;i<FF_SOUNDS;++i) if(app.sounds[i]) Mix_FreeChunk(app.sounds[i]);
    if(app.audio) Mix_CloseAudio();
    if(app.scene) SDL_DestroyTexture(app.scene);
    if(app.backdrop) SDL_DestroyTexture(app.backdrop);
    if(app.renderer) SDL_DestroyRenderer(app.renderer);
    if(app.window) SDL_DestroyWindow(app.window);
    IMG_Quit();SDL_Quit();return result;
}
