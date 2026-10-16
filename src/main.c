#include "game.h"
#include "input.h"
#include "fault.h"
#include "netplay.h"
#include "wz.h"
#include "mod.h"
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
    const char *assets; const FF_Mods *mods;
    int levels[16], level_count;   /* the import's other original levels, by frame number */
} App;
/* A mod's own file wins; otherwise the player's imported original. */
static bool image_path(const App *app,int id,char *path,size_t capacity) {
    if(id<0||id>=FF_IMAGES) return false;
    if(app->mods&&app->mods->image_path[id]) return snprintf(path,capacity,"%s",app->mods->image_path[id])<(int)capacity;
    if(!app->assets||id>=FF_ORIGINAL_IMAGES) return false;
    return snprintf(path,capacity,"%s/image-21-%d.png",app->assets,id)<(int)capacity;
}
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
        if(c=='.') rect(app,x+2*scale,y+4*scale,scale,scale);
        if(c==':') {rect(app,x+2*scale,y+scale,scale,scale);rect(app,x+2*scale,y+3*scale,scale,scale);}
        if(c=='_') rect(app,x,y+4*scale,5*scale,scale);
        if(c=='/') for(int yy=0;yy<5;++yy) rect(app,x+(4-yy)*scale,y+yy*scale,scale,scale);
    }
}
static void centered(App *app,int y,int scale,const char *s) {text(app,(FF_W-(int)strlen(s)*6*scale)/2,y,scale,s);}
static Image *load_image(App *app,int id) {
    if(id<0||id>=FF_IMAGES) return NULL;
    Image *image=&app->images[id];
    if(image->texture) return image;
    char path[4096];
    if(!image_path(app,id,path,sizeof(path))) return NULL;
    SDL_Surface *s=IMG_Load(path);if(!s) return NULL;
    image->w=s->w;image->h=s->h;image->texture=SDL_CreateTextureFromSurface(app->renderer,s);SDL_FreeSurface(s);
    return image->texture?image:NULL;
}
/* Seats 3 and 4 reuse the blue and red furry with the body hue turned to
 * green and yellow, computed from the player's own art at load time. */
static Image *load_tinted(App *app,int id,int seat) {
    if(seat<2) return load_image(app,id);
    if(id<0||id>=FF_IMAGES) return NULL;
    Image *image=&app->tinted[seat-2][id];
    if(image->texture) return image;
    char path[4096];
    if(!image_path(app,id,path,sizeof(path))) return NULL;
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
/* A mod weapon's own image in the hand, mirrored when the furry looks left. */
static void held(App *app,const FF_Arena *a,int id,int x,int y,bool left) {
    Image *im=load_image(app,id);if(!im) return;
    int anchor=left?im->w-1-a->hot_x[id]:a->hot_x[id];
    SDL_Rect dest={x-anchor,y-a->hot_y[id],im->w,im->h};
    SDL_RenderCopyEx(app->renderer,im->texture,NULL,&dest,0,NULL,left?SDL_FLIP_HORIZONTAL:SDL_FLIP_NONE);
}
/* Ticks a sequence shows before a one-time animation has finished. */
static uint32_t sequence_ticks(const FF_Sequence *s) {
    return s->speed>0?(uint32_t)((s->count*100+s->speed-1)/s->speed):(uint32_t)s->count*4u;
}
/* Like the original, the plain hand is swapped for the shooting hand only while a
 * punch or shot plays: the fist anim 12, or the weapon's 13 ice, 14 rocket, 15 flame.
 * A looping weapon animation stays up while the trigger keeps being pulled. */
static bool shooting_hand(const FF_Arena *a,const FF_Game *g,int i,int dir,int *image,bool *custom) {
    const FF_Player *p=&g->players[i];
    bool punch=g->punched[i]&&(!g->fired[i]||g->punched[i]>=g->fired[i]);
    uint32_t start=punch?g->punched[i]:g->fired[i];
    if(!start) return false;
    uint32_t since=g->tick-start;
    if(!punch&&p->weapon==FF_FISTS) return false;
    if(!punch&&a->weapons[p->weapon].hand_image>=0) {*custom=true;*image=a->weapons[p->weapon].hand_image;return since<12;}
    int anim=punch?12:p->weapon==FF_ICE?13:p->weapon==FF_ROCKET?14:15;
    const FF_Sequence *s=&a->sprites[i&1][4][anim][dir];
    if(!s->count) s=&a->sprites[i&1][4][anim][0];
    if(!s->count) return false;
    if(since>=(s->once?sequence_ticks(s):12u)) return false;
    *custom=false;*image=s->image[ff_sequence_frame(s,since,!s->once)];
    return true;
}
static void draw_player(App *app,const FF_Arena *a,const FF_Game *g,int i) {
    const FF_Player *p=&g->players[i];if(!p->active||!p->lives||p->respawn||(p->invulnerable&&g->tick%4<2)) return;
    int x=p->x/FF_FP,y=p->y/FF_FP,dir=p->facing<0;
    int anim=p->grounded?(abs(p->vx)>FF_FP/4?1:0):(p->vy<0?7:8);
    if(a->imported) {
        /* The source uses independent feet/body/hand/hat objects at one origin. */
        int shooting=-1;bool custom=false;
        bool armed=shooting_hand(a,g,i,dir,&shooting,&custom);
        for(int part=0;part<FF_PARTS;++part) {
            if(part==2&&armed) continue;
            if(part==4) {
                if(!armed) continue;
                if(custom) held(app,a,shooting,x,y-16,dir);else sprite(app,a,shooting,x,y-16);
                continue;
            }
            int id=animation_image(a,i,part,anim,dir,g->tick);
            if(part==1) sprite_for(app,a,id,x,y-16,i);else sprite(app,a,id,x,y-16);
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
/* Counters are right-aligned on their placement and stand on it, as in the original. */
static void counter(App *app,const FF_Hud *h,FF_Point at,int value) {
    char s[16];snprintf(s,sizeof(s),"%d",value<0?0:value);
    int x=at.x;
    for(int i=(int)strlen(s)-1;i>=0;--i) {
        Image *im=load_image(app,h->digits[s[i]-'0']);if(!im) return;
        x-=im->w;SDL_Rect dest={x,at.y-im->h,im->w,im->h};SDL_RenderCopy(app->renderer,im->texture,NULL,&dest);
    }
}
static void stretched(App *app,int id,int x,int y,int w,int h) {
    Image *im=load_image(app,id);if(!im||w<=0) return;
    /* The bar images are short vertical gradients: widen their middle column. */
    SDL_Rect src={im->w/2,0,1,im->h},dest={x,y,w,h};SDL_RenderCopy(app->renderer,im->texture,&src,&dest);
}
/* The original panel is part of the backdrop; this fills in its counters, the
 * weapon in hand, the jetpack fuel and both health bars around the centre line. */
static void original_hud(App *app,const FF_Arena *a,const FF_Game *g) {
    const FF_Hud *h=&a->hud;
    for(int i=0;i<2;++i) {
        const FF_Player *p=&g->players[i];
        counter(app,h,h->field[i][FF_HUD_LIVES],p->lives);
        counter(app,h,h->field[i][FF_HUD_SCORE],p->score);
        counter(app,h,h->field[i][FF_HUD_AMMO],p->weapon==FF_FISTS?0:p->ammo);
        const FF_Sequence *w=&h->weapon[p->weapon<4?p->weapon:0];
        if(p->weapon>=4) {int id=a->weapons[p->weapon].pickup_image;FF_Point at=h->field[i][FF_HUD_ITEM];
            if(id>=0) sprite(app,a,id,at.x+a->hot_x[id],at.y+a->hot_y[id]);}
        else if(w->count) sprite(app,a,w->image[ff_sequence_frame(w,g->tick,true)],h->field[i][FF_HUD_ITEM].x,h->field[i][FF_HUD_ITEM].y);
        if(h->fuel_width&&p->fuel) {
            rgb(app,h->fuel_color);FF_Point f=h->field[i][FF_HUD_FUEL];
            rect(app,f.x,f.y,p->fuel*h->fuel_width/300,h->fuel_height);
        }
    }
    if(h->bar_right>h->bar_left) {
        Image *white=load_image(app,h->bar[0]);int height=white?white->h:24;
        int top=h->bar_at.y-(white?a->hot_y[h->bar[0]]:12);
        int left=h->bar_at.x-h->bar_left,right=h->bar_right-h->bar_at.x;
        const FF_Player *blue=&g->players[0],*red=&g->players[1];
        if(blue->lives&&!blue->respawn) {int w=blue->health*left/100;stretched(app,h->bar[1],h->bar_at.x-w,top,w,height);}
        if(red->lives&&!red->respawn) {int w=red->health*right/100;stretched(app,h->bar[2],h->bar_at.x,top,w,height);}
        if(white) {SDL_Rect dest={h->bar_at.x-white->w/2,top,white->w,height};SDL_RenderCopy(app->renderer,white->texture,NULL,&dest);}
    }
}
static void hud(App *app,const FF_Arena *a,const FF_Game *g) {
    if(a->hud.on&&g->players[0].active&&g->players[1].active&&!g->players[2].active&&!g->players[3].active) {original_hud(app,a,g);return;}
    color(app,12,20,33);rect(app,0,560,800,40);
    char s[120];
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
        else if(wide) snprintf(s,sizeof(s),"%s %d  HP %d",a->weapons[p->weapon].name,p->ammo,p->health);
        else snprintf(s,sizeof(s),"%s %d",a->weapons[p->weapon].name,p->ammo);
        text(app,x,590,1,s);
        if(p->lives) {color(app,220,194,75);rect(app,x+(wide?195:bar-75),590,p->fuel/(wide?2:4),5);}
    }
}
static void draw_help(App *app);
/* The water's top above a point, or -1 when the point is not under water. */
static int water_top(const FF_Arena *a,int x,int y) {
    int top=-1;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(d->kind==FF_WATER&&x>=d->x&&x<d->x+d->w&&y>=d->y&&(top<0||d->y<top)) top=d->y;
    }
    return top;
}
/* A fan under water blows a bubble every 12 ticks, as in the original. Bubbles are
 * scenery, worked out from the tick alone: they drift with the fan's draught until
 * they reach the surface or a wall, then pop. */
static void draw_bubbles(App *app,const FF_Arena *a,uint32_t tick) {
    const FF_Sequence *rise=&a->bubble_sprites[0],*pop=&a->bubble_sprites[1];
    if(!rise->count) return;
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];
        if(d->kind<FF_FAN_LEFT||d->kind>FF_FAN_UP) continue;
        int cx=d->x+d->w/2,cy=d->y+d->h/2,surface=water_top(a,cx,cy);
        if(surface<0) continue;
        /* Half pixels per tick; sideways bubbles still rise a little. */
        int dx=d->kind==FF_FAN_LEFT?-3:d->kind==FF_FAN_RIGHT?3:0,dy=d->kind==FF_FAN_UP?-3:-1;
        for(uint32_t k=0;k<6;++k) {
            uint32_t age=(tick+(uint32_t)i*5u)%12u+k*12u,end=0;
            while(end<60) {
                int x=cx+dx*(int)end/2,y=cy+dy*(int)end/2;
                if(y<surface||x<0||x>=FF_W||y>=FF_H||a->mask[y][x]==FF_SOLID) break;
                ++end;
            }
            uint32_t at=age<end?age:end;
            int x=cx+dx*(int)at/2,y=cy+dy*(int)at/2;
            if(age<end) sprite(app,a,rise->image[ff_sequence_frame(rise,age,true)],x,y);
            else if(pop->count&&age-end<(uint32_t)pop->count*3u) sprite(app,a,pop->image[(age-end)/3u],x,y);
        }
    }
}
static void draw(App *app,const FF_Arena *a,const FF_Game *g,bool help,bool paused) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    for(int i=0;i<a->device_count;++i) {
        const FF_Device *d=&a->devices[i];FF_Point pos=ff_device_position(a,i,g->tick);
        if(d->image<0) continue;
        /* Device positions are the first frame's corner; later frames keep its hot spot. */
        const FF_Sequence *idle=&a->device_sprites[d->kind][0],*fired=&a->device_sprites[d->kind][1];
        uint32_t since=g->tick-g->device_hit[i];int id=d->image;
        if(fired->count&&g->device_hit[i]&&(uint64_t)since*(uint32_t)fired->speed<100u*(uint64_t)fired->count)
            id=fired->image[ff_sequence_frame(fired,since,false)];
        else if(idle->count) id=idle->image[ff_sequence_frame(idle,g->tick,true)];
        sprite(app,a,id,pos.x+a->hot_x[d->image],pos.y+a->hot_y[d->image]);
    }
    draw_bubbles(app,a,g->tick);
    for(int i=0;i<FF_HAZARDS;++i) {
        const FF_Hazard *h=&g->hazards[i];if(!h->life) continue;
        const FF_Sequence *seq=&a->hazard_sprites[h->kind-1][h->vx<0];
        if(!seq->count) seq=&a->hazard_sprites[h->kind-1][0];
        int x=h->x/FF_FP,y=h->y/FF_FP;
        if(seq->count) sprite(app,a,seq->image[ff_sequence_frame(seq,g->tick,true)],x,y);
        else {color(app,245,80,35);rect(app,x-6,y-6,12,12);color(app,255,220,90);rect(app,x-2,y-10,4,5);}
    }
    for(int i=0;i<FF_PICKUPS;++i) {const FF_Pickup *p=&g->pickups[i];if(!p->active) continue;
        int weapon=ff_pickup_weapon(p->kind);
        int id=p->kind<=5?a->pickup_images[p->kind]:-1;const FF_Sequence *spin=&a->pickup_sprites[p->kind<=5?p->kind:0];
        if(weapon&&a->weapons[weapon].pickup_image>=0) id=a->weapons[weapon].pickup_image;
        else if(spin->count) id=spin->image[ff_sequence_frame(spin,g->tick,true)];
        if(id>=0) sprite(app,a,id,p->x,p->y);
        else {color(app,220,190,70);rect(app,p->x-9,p->y-9,18,18);color(app,20,30,40);
            const char *names[]={"","I","F","R","H","J","W","W","W","W"};text(app,p->x-5,p->y-5,2,names[p->kind<10?p->kind:6]);}
    }
    for(int i=0;i<FF_PLAYERS;++i) draw_player(app,a,g,i);
    for(int i=0;i<FF_SHOTS;++i) {const FF_Shot *s=&g->shots[i];if(!s->life) continue;
        const FF_Weapon *w=&a->weapons[s->kind];
        const FF_Sequence *fire=&a->fire_sprites[s->life<=20];
        if(w->flame&&w->shot_image<0&&fire->count) {
            int frame=s->life<=20?(20-s->life)*fire->count/20:(270-s->life)/4%fire->count;
            sprite(app,a,fire->image[frame],s->x/FF_FP,s->y/FF_FP);continue;
        }
        if(w->flame&&s->life<=20&&s->life%4<2) continue;
        int id=w->shot_image>=0?w->shot_image:s->kind<4?a->shot_images[s->kind]:-1;
        if(id>=0) {
            Image *im=load_image(app,id);
            if(im) {
                if(w->homing) {
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
    hud(app,a,g);
    if(help||paused||g->winner>=0) {
        color(app,12,20,33);rect(app,90,160,620,270);color(app,232,242,250);
        if(help) draw_help(app);
        else if(paused) centered(app,270,4,"PAUSED - P TO PLAY");
        else {
            char s[64];
            if(g->winner==FF_DRAW) snprintf(s,sizeof(s),"DRAW");
            else if(g->winner>=FF_TEAM_WIN) snprintf(s,sizeof(s),"TEAM %s WINS",g->winner==FF_TEAM_WIN?"BLUE":"RED");
            else snprintf(s,sizeof(s),"%s WINS",seat_name[g->winner]);
            centered(app,252,4,s);centered(app,302,2,"NEXT ROUND STARTS SHORTLY");
        }
    }
}
static void draw_net_overlay(App *app,const FF_Netplay *np,FF_Wz *wz) {
    color(app,12,20,33);rect(app,690,4,106,14);color(app,140,220,140);text(app,694,7,1,np->virtual_net?"WARPZONE":"ONLINE");
    char line[64];
    for(int i=0;np->virtual_net&&ff_wz_peer_line(wz,i,line,sizeof(line));++i) {
        int w=(int)strlen(line)*6+8;color(app,12,20,33);rect(app,796-w,19+i*12,w,12);color(app,170,185,200);text(app,800-w,21+i*12,1,line);
    }
    if(np->stalled>10) {color(app,12,20,33);rect(app,250,20,300,30);color(app,255,230,120);centered(app,28,2,"WAITING FOR NETWORK");}
    if(np->rb.desync!=UINT32_MAX) {color(app,12,20,33);rect(app,250,52,300,22);color(app,250,120,100);centered(app,58,2,"OUT OF SYNC");}
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
typedef struct { unsigned joined; int mode, arena, arenas; uint8_t previous[FF_PLAYERS]; } Lobby;
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
        if((pressed&FF_PUNCH)&&(l->joined&(1u<<i))&&l->arenas>1) l->arena=(l->arena+1)%l->arenas;
    }
}
static void draw_lobby(App *app,const Lobby *l,const FF_Input *in,const char *arena) {
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
    char line[96];snprintf(line,sizeof(line),"%s   ARENA: %s",l->mode==FF_TEAMS?"MODE: 2 VS 2":"MODE: FREE FOR ALL",arena);
    centered(app,362,2,line);
    color(app,170,185,200);
    if(app->mods&&app->mods->mod_count) {
        snprintf(line,sizeof(line),"MODS: %.86s",app->mods->names);color(app,255,230,120);centered(app,384,1,line);color(app,170,185,200);
    }
    centered(app,400,1,l->arenas>1?"A/JUMP JOIN  B/FIRE LEAVE  Y/JETPACK MODE  X/PUNCH ARENA":"A/JUMP JOIN   B/FIRE LEAVE   Y/JETPACK CHANGE MODE");
    int n=seat_count(l->joined);
    color(app,232,242,250);
    if(lobby_ready(l)) centered(app,440,3,"START OR ENTER TO PLAY");
    else if(l->mode==FF_TEAMS) centered(app,440,2,"2 VS 2 NEEDS FOUR PLAYERS");
    else centered(app,440,2,n?"ONE MORE PLAYER NEEDED":"TWO PLAYERS NEEDED");
    color(app,170,185,200);centered(app,480,2,"H OR BACK: HOST ONLINE   J: JOIN   R OR RB: RANKED");
    centered(app,510,1,"PLAYERS WHO JOINED HERE PLAY ONLINE TOGETHER");
    centered(app,525,1,"F1 CONTROLS   ESC QUIT");
}
static void draw_code_entry(App *app,const char *code,const char *error) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    color(app,12,20,33);rect(app,30,60,740,480);
    color(app,232,242,250);centered(app,110,4,"JOIN ONLINE");
    color(app,170,185,200);centered(app,175,2,"TYPE OR PASTE THE ROOM CODE OR JOIN CODE");
    centered(app,200,1,"OR THEIR ADDRESS ON THE SAME NETWORK, E.G. 192.168.1.20:27590");
    color(app,30,38,50);rect(app,100,250,600,70);color(app,232,242,250);
    centered(app,268,4,code);
    if((SDL_GetTicks()/400)%2) rect(app,(FF_W+(int)strlen(code)*24)/2,268,4,20);
    if(error&&*error) {color(app,250,120,100);centered(app,350,2,error);}
    color(app,170,185,200);centered(app,430,2,"ENTER JOIN   CTRL V PASTE   ESC BACK");
}
static void draw_result(App *app,const FF_Netplay *np,const FF_Wz *wz) {
    color(app,12,20,33);rect(app,150,150,500,300);
    color(app,232,242,250);centered(app,175,4,"MATCH OVER");
    for(int s=0,row=0;s<FF_PLAYERS;++s) if(np->final_score[s]>=0) {
        char name[20],line[48];if(!ff_wz_seat_name(wz,s,name,sizeof(name))) snprintf(name,sizeof(name),"%s",seat_name[s]);
        snprintf(line,sizeof(line),"%s  %d %s",name,np->final_score[s],np->final_score[s]==1?"WIN":"WINS");
        color(app,seat_color[s][0],seat_color[s][1],seat_color[s][2]);centered(app,230+row++*26,2,line);
    }
    char line[64];snprintf(line,sizeof(line),"FINAL STATE %08X",np->final_hash);color(app,170,185,200);centered(app,345,1,line);
    color(app,255,230,120);
    centered(app,370,2,wz->match_state[0]?wz->match_state:wz->reported?"WAITING FOR THE OTHER RESULTS":"SENDING THE RESULT");
    color(app,170,185,200);centered(app,420,1,"ESC/BACK LEAVES");
}
static const char *queue_ids[]={"1v1","ffa","2v2"},*queue_names[]={"1 VS 1","FREE FOR ALL - 4","2 VS 2"};
static void draw_ranked_menu(App *app,int choice,const FF_Wz *wz) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    color(app,12,20,33);rect(app,30,60,740,480);
    color(app,232,242,250);centered(app,100,4,"RANKED ONLINE");
    color(app,170,185,200);centered(app,150,1,"ONE PLAYER PER DEVICE - FIRST TO 3 ROUND WINS");
    for(int i=0;i<3;++i) {
        if(i==choice) {color(app,255,230,120);rect(app,230,200+i*60,340,44);color(app,12,20,33);}
        else color(app,232,242,250);
        centered(app,212+i*60,3,queue_names[i]);
    }
    color(app,170,185,200);centered(app,400,2,wz->online?wz->status:"WARPZONE IS NOT REACHABLE");
    centered(app,450,2,"UP DOWN CHOOSE   ENTER OR A FIND A MATCH");centered(app,480,2,"ESC/BACK RETURNS");
}
static void draw_warpzone(App *app,const FF_Wz *wz,const char *name,bool naming) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    color(app,12,20,33);rect(app,30,60,740,480);
    color(app,232,242,250);centered(app,110,4,"WARPZONE");
    if(naming) {
        color(app,170,185,200);centered(app,175,2,"CHOOSE YOUR NAME FOR ONLINE PLAY");
        centered(app,200,1,"3 TO 16 LETTERS, DIGITS, _ OR -  - SHARED WITH ALL WARPZONE GAMES");
        color(app,30,38,50);rect(app,100,250,600,70);color(app,232,242,250);centered(app,268,4,name);
        if((SDL_GetTicks()/400)%2) rect(app,(FF_W+(int)strlen(name)*24)/2,268,4,20);
        color(app,170,185,200);centered(app,430,2,"ENTER CONFIRMS   ESC BACK");
    } else {
        color(app,232,242,250);centered(app,240,2,wz->status);
        if(wz->queued) {color(app,170,185,200);centered(app,280,1,"YOU GET A MATCH AS SOON AS ENOUGH PLAYERS ARE LOOKING");}
        color(app,170,185,200);centered(app,430,2,"ESC/BACK CANCELS");
    }
    if(wz->error[0]) {color(app,250,120,100);centered(app,350,2,wz->error);}
}
static void draw_online(App *app,const FF_Netplay *np,bool copied,FF_Wz *wz) {
    SDL_RenderCopy(app->renderer,app->backdrop,NULL,NULL);
    color(app,12,20,33);rect(app,30,40,740,520);
    color(app,232,242,250);centered(app,62,4,"ONLINE MATCH");
    if(np->phase==FF_NP_ENDED) {
        color(app,250,120,100);centered(app,250,3,np->ended);
        color(app,170,185,200);centered(app,330,2,"ENTER OR A TO GO BACK");return;
    }
    if(np->virtual_net) {
        color(app,170,185,200);
        if(wz->ranked) {char s[40];snprintf(s,sizeof(s),"RANKED %s",queue_names[wz->team_size==2?2:wz->teams>2?1:0]);centered(app,112,2,s);}
        else if(np->code[0]) {
            centered(app,112,2,"ROOM CODE");color(app,255,230,120);centered(app,140,5,np->code);color(app,170,185,200);
            centered(app,182,1,copied?"COPIED TO THE CLIPBOARD - SEND IT TO THE OTHER PLAYERS":"SEND IT TO THE OTHER PLAYERS");
        }
        char line[64];
        for(int i=0;i<3&&ff_wz_peer_line(wz,i,line,sizeof(line));++i) centered(app,198+i*10,1,line);
    } else if(np->host) {
        color(app,170,185,200);centered(app,112,2,"JOIN CODE");
        color(app,255,230,120);centered(app,140,5,np->code);
        color(app,170,185,200);
        centered(app,182,1,copied?"COPIED TO THE CLIPBOARD - SEND IT TO THE OTHER PLAYERS":"SEND IT TO THE OTHER PLAYERS");
        char s[64];snprintf(s,sizeof(s),"SAME NETWORK: %s",np->lan_text);centered(app,198,1,s);
    } else {
        color(app,170,185,200);centered(app,125,2,"JOINING");color(app,232,242,250);centered(app,155,3,np->code);
    }
    color(app,232,242,250);centered(app,222,2,np->status);
    for(int i=0;i<FF_PLAYERS;++i) {
        int x=55+i*180;bool taken=(np->seats>>i)&1u;bool mine=taken&&np->owner[i]==(np->host?0:np->me)&&(np->host||np->me>=0);
        color(app,taken?seat_body[i][0]/3:30,taken?seat_body[i][1]/3:38,taken?seat_body[i][2]/3:50);rect(app,x,255,150,120);
        color(app,seat_color[i][0],seat_color[i][1],seat_color[i][2]);rect(app,x,255,150,6);
        char s[32];snprintf(s,sizeof(s),"PLAYER %d",i+1);text(app,x+12,272,2,s);text(app,x+12,296,2,seat_name[i]);
        if(np->mode==FF_TEAMS) {color(app,200,210,220);text(app,x+12,320,1,i&1?"TEAM RED":"TEAM BLUE");}
        color(app,232,242,250);text(app,x+12,342,2,!taken?"OPEN":mine?"YOU":"ONLINE");
    }
    color(app,232,242,250);centered(app,400,2,np->mode==FF_TEAMS?"MODE: 2 VS 2":"MODE: FREE FOR ALL");
    color(app,170,185,200);
    if(np->host&&wz->ranked) centered(app,440,2,"THE MATCH STARTS WHEN EVERYONE IS HERE");
    else if(np->host) {
        centered(app,440,3,ff_np_can_start(np,np->mode)?"START OR ENTER TO PLAY":np->mode==FF_TEAMS?"2 VS 2 NEEDS FOUR PLAYERS":"ANOTHER PLAYER NEEDED");
        centered(app,480,1,"Y/JETPACK OR TAB CHANGES MODE");
    } else centered(app,440,2,np->me>=0?(wz->ranked?"THE MATCH STARTS WHEN EVERYONE IS HERE":"THE HOST STARTS THE MATCH"):"");
    centered(app,520,1,"ESC/BACK LEAVES");
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
    const FF_Sequence *more[FF_WIND_UP*2+5+4];int n=0;
    for(int k=1;k<=FF_WIND_UP;++k) {more[n++]=&a->device_sprites[k][0];more[n++]=&a->device_sprites[k][1];}
    for(int k=1;k<6;++k) more[n++]=&a->pickup_sprites[k];
    for(int k=0;k<4;++k) more[n++]=&a->hud.weapon[k];
    for(int k=0;k<n;++k) for(int i=0;i<more[k]->count;++i) if(!load_image(app,more[k]->image[i])) return false;
    for(int k=1;k<=a->rules.weapons&&k<FF_WEAPONS;++k) {
        const FF_Weapon *w=&a->weapons[k];
        if((w->shot_image>=0&&!load_image(app,w->shot_image))||(w->pickup_image>=0&&!load_image(app,w->pickup_image))||
           (w->hand_image>=0&&!load_image(app,w->hand_image))) return false;
    }
    if(a->hud.on) {
        for(int i=0;i<10;++i) if(!load_image(app,a->hud.digits[i])) return false;
        for(int i=0;i<3;++i) if(a->hud.bar[i]>=0&&!load_image(app,a->hud.bar[i])) return false;
    }
    return true;
}
static bool read_png(const char *path,int *w,int *h,uint8_t **rgba) {
    SDL_Surface *loaded=IMG_Load(path);if(!loaded) return false;
    SDL_Surface *s=SDL_ConvertSurfaceFormat(loaded,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(loaded);
    if(!s) return false;
    *rgba=malloc((size_t)s->w*(size_t)s->h*4);
    if(*rgba) {
        SDL_LockSurface(s);
        for(int y=0;y<s->h;++y) memcpy(*rgba+(size_t)y*(size_t)s->w*4,(uint8_t *)s->pixels+y*s->pitch,(size_t)s->w*4);
        SDL_UnlockSurface(s);
    }
    *w=s->w;*h=s->h;SDL_FreeSurface(s);return *rgba!=NULL;
}
/* Mod images without a stated hot spot turn around their centre. */
static void mod_hotspots(App *app,FF_Arena *a) {
    if(!app->mods) return;
    for(int id=FF_ORIGINAL_IMAGES;id<FF_IMAGES;++id) if(app->mods->center[id]) {
        Image *im=load_image(app,id);if(im) {a->hot_x[id]=im->w/2;a->hot_y[id]=im->h/2;}
    }
}
typedef struct { FF_Arena *base; FF_Mods *mods; int failed; } ModLoad;
static void load_mod(const char *dir,const char *name,void *user) {
    ModLoad *l=user;char error[256];
    static FF_Arena trial;trial=*l->base;
    /* A broken mod is left out whole, never half applied. */
    if(ff_mod_apply(&trial,l->mods,dir,name,error,sizeof(error))) *l->base=trial;
    else {fprintf(stderr,"%s\n",error);++l->failed;}
}
/* Arena 0 is the imported original (or practice); the rest are mod levels. */
/* Arena 0 is the import's first level, then its other original levels, then mod levels. */
static void arena_label(const App *app,const FF_Arena *base,const FF_Mods *mods,int index,char *name,size_t capacity) {
    if(index>app->level_count&&index<=app->level_count+mods->level_count) snprintf(name,capacity,"%s",mods->level_name[index-app->level_count-1]);
    else if(app->level_count) snprintf(name,capacity,"LEVEL %d",index+1);
    else snprintf(name,capacity,"%s",base->imported?"ORIGINAL":"PRACTICE");
}
static bool choose_arena(App *app,FF_Arena *arena,const FF_Arena *base,FF_Mods *mods,int index,char *name,size_t capacity) {
    char error[256];
    for(int id=FF_MOD_IMAGES;id<FF_IMAGES;++id) if(app->images[id].texture) {SDL_DestroyTexture(app->images[id].texture);app->images[id].texture=NULL;}
    *arena=*base;mods->next_picture=FF_MOD_IMAGES;
    if(index<0||index>app->level_count+mods->level_count) index=0;
    arena_label(app,base,mods,0,name,capacity);
    if(index>0&&index<=app->level_count) {
        static FF_Arena level;char path[4096];
        snprintf(path,sizeof(path),"%s/level-%d.ff",app->assets,app->levels[index-1]);
        if(!ff_arena_load(&level,path,error,sizeof(error))) {fprintf(stderr,"%s\n",error);return false;}
        ff_arena_take_level(arena,&level);
    } else if(index>app->level_count) {
        if(!ff_level_apply(arena,mods,mods->level_path[index-app->level_count-1],read_png,error,sizeof(error))) {fprintf(stderr,"%s\n",error);*arena=*base;return false;}
    }
    arena_label(app,base,mods,index,name,capacity);
    mod_hotspots(app,arena);
    if(!assets_ready(app,arena)) {fprintf(stderr,"Images of arena %s are missing\n",name);*arena=*base;return false;}
    if(app->backdrop&&SDL_SetRenderTarget(app->renderer,app->backdrop)==0) {background(app,arena);SDL_SetRenderTarget(app->renderer,NULL);}
    return true;
}
/* A room's mod set replaces ours: base arena again, then exactly the room's mods. */
static bool reload_mods(App *app,FF_Arena *base,FF_Mods *mods,const char *data,char paths[][1024],int count) {
    char error[256],path[4096];
    for(int id=FF_ORIGINAL_IMAGES;id<FF_IMAGES;++id) if(app->images[id].texture) {SDL_DestroyTexture(app->images[id].texture);app->images[id].texture=NULL;}
    for(int k=0;k<2;++k) for(int id=0;id<FF_IMAGES;++id) if(app->tinted[k][id].texture) {SDL_DestroyTexture(app->tinted[k][id].texture);app->tinted[k][id].texture=NULL;}
    for(int id=0;id<FF_ORIGINAL_IMAGES;++id) if(mods->image_path[id]&&app->images[id].texture) {SDL_DestroyTexture(app->images[id].texture);app->images[id].texture=NULL;}
    ff_mods_free(mods);
    if(data) {snprintf(path,sizeof(path),"%s/arena.ff",data);if(!ff_arena_load(base,path,error,sizeof(error))) return false;}
    else ff_arena_practice(base);
    ModLoad load={base,mods,0};
    for(int i=0;i<count;++i) {
        /* .../mods/funny-furries/<name>/<version>/files */
        char name[128]="mod";const char *end=strstr(paths[i],"/files");const char *v=NULL,*n=NULL;
        for(const char *c=paths[i];end&&c<end;++c) if(*c=='/') {n=v;v=c;}
        if(n&&v) snprintf(name,sizeof(name),"%.*s",(int)(v-n-1),n+1);
        load_mod(paths[i],name,&load);
    }
    return !load.failed;
}
static bool parse_ticks(const char *s,int *ticks) {
    char *end;errno=0;long value=strtol(s,&end,10);
    if(errno||*end||value<1||value>10000000) return false;
    *ticks=(int)value;return true;
}
int main(int argc,char **argv) {
    /* Start-up stages, reported only when the first frame is slow to come. */
    uint32_t started=ff_net_ms(),stage[4]={0};
    const char *mod_dirs[16];int mod_dir_count=0,arena_index=0,level_number=0;bool no_mods=false;
    const char *data=NULL,*screenshot=NULL,*join=NULL,*wz_code=NULL,*ranked=NULL;bool wz_host=false;int ticks=0,players=2,local_players=0;bool auto_play=false,fullscreen=false,teams=false,show_lobby=false,host=false;
    for(int i=1;i<argc;++i) {
        if(!strcmp(argv[i],"--fullscreen")) fullscreen=true;
        else if(!strcmp(argv[i],"--data")&&i+1<argc) data=argv[++i];
        else if(!strcmp(argv[i],"--mod")&&i+1<argc&&mod_dir_count<16) mod_dirs[mod_dir_count++]=argv[++i];
        else if(!strcmp(argv[i],"--no-mods")) no_mods=true;
        else if(!strcmp(argv[i],"--arena")&&i+1<argc&&parse_ticks(argv[i+1],&arena_index)) ++i;
        else if(!strcmp(argv[i],"--level")&&i+1<argc&&parse_ticks(argv[i+1],&level_number)) ++i;
        else if(!strcmp(argv[i],"--smoke")&&i+1<argc&&parse_ticks(argv[i+1],&ticks)) {++i;auto_play=true;}
        else if(!strcmp(argv[i],"--screenshot")&&i+1<argc) screenshot=argv[++i];
        else if(!strcmp(argv[i],"--players")&&i+1<argc&&argv[i+1][0]>='2'&&argv[i+1][0]<='4'&&!argv[i+1][1]) players=argv[++i][0]-'0';
        else if(!strcmp(argv[i],"--teams")) teams=true;
        else if(!strcmp(argv[i],"--lobby")) show_lobby=true;
        else if(!strcmp(argv[i],"--host")) host=true;
        else if(!strcmp(argv[i],"--join")&&i+1<argc) join=argv[++i];
        else if(!strcmp(argv[i],"--warpzone-host")) wz_host=true;
        else if(!strcmp(argv[i],"--warpzone-join")&&i+1<argc) ++i;   /* the library reads it */
        else if(!strncmp(argv[i],"warpzone://",11)) {}
        else if(!strcmp(argv[i],"--warpzone-code")&&i+1<argc) wz_code=argv[++i];
        else if(!strcmp(argv[i],"--ranked")&&i+1<argc&&(!strcmp(argv[i+1],"1v1")||!strcmp(argv[i+1],"ffa")||!strcmp(argv[i+1],"2v2"))) ranked=argv[++i];
        else if(!strcmp(argv[i],"--local")&&i+1<argc&&argv[i+1][0]>='1'&&argv[i+1][0]<='3'&&!argv[i+1][1]) local_players=argv[++i][0]-'0';
        else if(!strcmp(argv[i],"--help")) {puts("funny-furries [--fullscreen] [--data LOCAL_IMPORT] [--host | --join CODE] [--warpzone-host | --warpzone-join ROOM | --warpzone-code CODE | --ranked 1v1|ffa|2v2] [--local 1-3] [--mod DIR]... [--no-mods] [--arena N] [--level N] [--smoke TICKS [--players 2-4] [--teams] [--lobby]] [--screenshot FILE.bmp]\nWithout --data, play the asset-free practice arena. F1 shows controls.\n--host opens an online match and shows its join code; --join CODE joins one.\nThe --warpzone options do the same through Warpzone rooms (relay included) and its ranked queues.\nEveryone online needs the same arena import.\n--mod DIR loads a mod directory (docs/MODDING.md); without --no-mods the mods active in\nthe Warpzone launcher load too. --arena N starts on the N-th mod level, --level N on the original's level N.");return 0;}
        else {fprintf(stderr,"Unknown or incomplete option. Use --help.\n");return 2;}
    }
    if(teams&&players!=4) {fprintf(stderr,"--teams needs --players 4.\n");return 2;}
    if(host&&join) {fprintf(stderr,"Use either --host or --join.\n");return 2;}
    ff_fault_init();
    static FF_Arena arena,base;static FF_Mods mods;FF_Game game;App app={0};int result=1;char error[256];
    char arena_name[32]="",mod_hash[80]="";
    if(data) {
        char path[4096];if(snprintf(path,sizeof(path),"%s/arena.ff",data)>=(int)sizeof(path)||!ff_arena_load(&arena,path,error,sizeof(error))) {
            fprintf(stderr,"Cannot load local import. Run tools/import_arena.py first.\n");return 2;
        }
        app.assets=data;
        for(int n=0;n<64&&app.level_count<16;++n) {
            if(snprintf(path,sizeof(path),"%s/level-%d.ff",data,n)<(int)sizeof(path)&&ff_arena_exists(path)) app.levels[app.level_count++]=n;
        }
    } else ff_arena_practice(&arena);
    {
        /* Smoke runs only load the mods they name, so tests never depend on this machine's set. */
        ModLoad load={&arena,&mods,0};
        bool active=!auto_play||getenv("FF_MODS_ACTIVE");
        if(!no_mods&&active&&!getenv("FF_NO_MODS")) snprintf(mod_hash,sizeof(mod_hash),"%s",ff_mods_active(load_mod,&load));
        for(int i=0;i<mod_dir_count;++i) {const char *slash=strrchr(mod_dirs[i],'/');load_mod(mod_dirs[i],slash&&slash[1]?slash+1:mod_dirs[i],&load);}
        if(load.failed||mod_dir_count) mod_hash[0]=0;   /* not the launcher's exact set: no lockfile for rooms */
        base=arena;app.mods=&mods;
    }
    stage[0]=ff_net_ms();
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER|SDL_INIT_AUDIO)<0) goto fail;
    if(!(IMG_Init(IMG_INIT_PNG)&IMG_INIT_PNG)) goto fail;
    app.window=SDL_CreateWindow("Funny Furries 0.6.0 - test release",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,1000,750,SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI|(fullscreen?SDL_WINDOW_FULLSCREEN_DESKTOP:0));
    if(!app.window) goto fail;
    app.renderer=SDL_CreateRenderer(app.window,-1,SDL_RENDERER_ACCELERATED|SDL_RENDERER_PRESENTVSYNC);
    if(!app.renderer) app.renderer=SDL_CreateRenderer(app.window,-1,SDL_RENDERER_SOFTWARE);
    if(!app.renderer||SDL_RenderSetLogicalSize(app.renderer,FF_W,FF_H)<0) goto fail;
    app.scene=SDL_CreateTexture(app.renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,FF_W,FF_H);
    if(!app.scene) goto fail;
    stage[1]=ff_net_ms();
    if(data&&!assets_ready(&app,&base)) {fprintf(stderr,"Incomplete local image import.\n");result=2;goto cleanup;}
    app.backdrop=SDL_CreateTexture(app.renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,FF_W,FF_H);
    if(!app.backdrop||SDL_SetRenderTarget(app.renderer,app.backdrop)<0) goto fail;
    if(SDL_SetRenderTarget(app.renderer,NULL)<0) goto fail;
    if(arena_index>mods.level_count) {fprintf(stderr,"There is no mod arena %d.\n",arena_index);result=2;goto cleanup;}
    if(arena_index) arena_index+=app.level_count;   /* --arena counts mod levels only */
    if(level_number>1+app.level_count) {fprintf(stderr,"There is no level %d.\n",level_number);result=2;goto cleanup;}
    if(level_number>0) arena_index=level_number-1;
    if(!choose_arena(&app,&arena,&base,&mods,arena_index,arena_name,sizeof(arena_name))&&arena_index) {result=2;goto cleanup;}
    stage[2]=ff_net_ms();
    app.audio=Mix_OpenAudio(44100,AUDIO_S16SYS,2,1024)==0;
    if(app.audio) for(int i=0;i<FF_SOUNDS;++i) if(mods.sound_path[i]||(data&&arena.sound_ids[i]>=0)) {
        char path[4096];
        if(mods.sound_path[i]) snprintf(path,sizeof(path),"%s",mods.sound_path[i]);
        else snprintf(path,sizeof(path),"%s/sound-23-%d.wav",data,arena.sound_ids[i]);
        app.sounds[i]=Mix_LoadWAV(path);
        if(!app.sounds[i]) {fprintf(stderr,"Incomplete local sound import.\n");result=2;goto cleanup;}
        Mix_VolumeChunk(app.sounds[i],MIX_MAX_VOLUME/3);
    }
    stage[3]=ff_net_ms();
    ff_input_init(&app.input);
    ff_game_setup(&game,&arena,12345,(1u<<players)-1,teams?FF_TEAMS:FF_FFA);
    Lobby lobby={0};lobby.arena=arena_index;lobby.arenas=1+app.level_count+mods.level_count;
    /* Smoke runs stay off the network unless they test Warpzone itself. */
    bool wz_asked=wz_host||wz_code||ranked||getenv("WARPZONE_JOIN")||getenv("WARPZONE_HOST");
    for(int i=1;i<argc;++i) wz_asked|=!strcmp(argv[i],"--warpzone-join")||!strncmp(argv[i],"warpzone://",11);
    static FF_Wz wz;if(!auto_play||wz_asked) ff_wz_open(&wz,"0.6.0");
    wz.arena=&arena;
    bool naming=false,ranked_menu=false;char name_entry[20]="";int ranked_choice=0;uint32_t wz_deadline=0;
    if(ff_wz_launch(&wz,argc,argv)==2) wz_host=true;
    if(wz_host) ff_wz_host(&wz,local_players?local_players:1,teams?FF_TEAMS:FF_FFA);
    if(wz_code) ff_wz_join_code(&wz,wz_code,local_players?local_players:1);
    if(ranked) ff_wz_queue(&wz,ranked);
    if((wz_host||wz_code||ranked)&&!wz.available) {fprintf(stderr,"This build has no Warpzone support.\n");result=2;goto cleanup;}
    if(auto_play&&(wz_host||wz_code||ranked)) wz_deadline=SDL_GetTicks()+240000;
    static FF_Netplay np;bool entering=false,copied=false;char entry[40]="",entry_error[96]="",copied_code[20]="";
    uint8_t online_previous[FF_PLAYERS]={0};char online_result[128]="";
    if(host) ff_np_host(&np,&arena,local_players?local_players:1,FF_NET_PORT,!getenv("FF_NET_LAN_ONLY"));
    if(join&&!ff_np_join(&np,&arena,join,local_players?local_players:1,!getenv("FF_NET_LAN_ONLY"))) {fprintf(stderr,"%s\n",np.status);result=2;goto cleanup;}
    if(host&&np.phase==FF_NP_OFF) {fprintf(stderr,"%s\n",np.status);result=2;goto cleanup;}
    if(host||join) printf("online code=%s lan=%s\n",np.code,np.lan_text),fflush(stdout);
    bool running=true,help=false,paused=false,in_lobby=!auto_play||show_lobby;uint64_t previous=SDL_GetPerformanceCounter(),accumulator=0;
    uint64_t frequency=SDL_GetPerformanceFrequency();
    while(running) {
        SDL_Event event;bool start=false,back=false,leave=false,mode_key=false;
        snprintf(wz.lockfile,sizeof(wz.lockfile),"%s",mod_hash);snprintf(wz.arena_name,sizeof(wz.arena_name),"%s",arena_name);
        ff_wz_update(&wz,&np,&arena);
        if(wz.reload) {
            bool ok=true;
            if(wz.reload_mods) {
                ok=reload_mods(&app,&base,&mods,data,wz.mod_path,wz.mod_paths);
                snprintf(mod_hash,sizeof(mod_hash),"%s",ok?wz.room_lockfile:"");
                lobby.arenas=1+app.level_count+mods.level_count;
            }
            int wanted=0;char label[32];
            for(int i=1;i<lobby.arenas;++i) {arena_label(&app,&base,&mods,i,label,sizeof(label));if(!strcmp(label,wz.room_arena)) wanted=i;}
            ok=ok&&choose_arena(&app,&arena,&base,&mods,wanted,arena_name,sizeof(arena_name));
            lobby.arena=arena_index=ok?wanted:0;
            if(ok) ff_wz_reloaded(&wz,&np);
            else {ff_wz_leave(&wz,&np);snprintf(wz.error,sizeof(wz.error),"THE ROOM'S MODS DID NOT LOAD");}
        }
        bool wz_screen=np.phase==FF_NP_OFF&&wz.available&&(wz.busy||wz.pending);
        naming=wz_screen&&wz.pending&&wz.need_name;
        if(wz_deadline&&(int32_t)(SDL_GetTicks()-wz_deadline)>0) {fprintf(stderr,"warpzone: timed out (%s %s)\n",wz.status,wz.error);result=1;goto cleanup;}
        if(auto_play&&wz.error[0]&&np.phase==FF_NP_OFF) {fprintf(stderr,"warpzone: %s\n",wz.error);result=1;goto cleanup;}
        if(auto_play&&wz.ranked&&np.finished&&wz.match_state[0]) {
            snprintf(online_result,sizeof(online_result),"ranked match=%s frame=%u state=%08x result=%s",wz.match_id,np.final_frame,np.final_hash,wz.match_state);
            running=false;
        }
        static char announced[20];
        if(auto_play&&np.virtual_net&&np.code[0]&&strcmp(announced,np.code)) {snprintf(announced,sizeof(announced),"%s",np.code);printf("warpzone code=%s\n",np.code);fflush(stdout);}
        bool online=np.phase!=FF_NP_OFF,playing_online=np.phase==FF_NP_PLAYING;
        while(SDL_PollEvent(&event)) {
            ff_input_event(&app.input,&event);
            if(event.type==SDL_QUIT) running=false;
            if(event.type==SDL_WINDOWEVENT&&event.window.event==SDL_WINDOWEVENT_FOCUS_LOST&&!auto_play&&!online) paused=true;
            if(naming&&event.type==SDL_TEXTINPUT) {
                for(const char *c=event.text.text;*c;++c) {
                    char ch=(char)(*c>='a'&&*c<='z'?*c-32:*c);size_t n=strlen(name_entry);
                    if(n<16&&((ch>='A'&&ch<='Z')||(ch>='0'&&ch<='9')||ch=='-'||ch=='_')) {name_entry[n]=ch;name_entry[n+1]=0;}
                }
                continue;
            }
            if(wz_screen&&event.type==SDL_KEYDOWN&&!event.key.repeat) {
                SDL_Keycode key=event.key.keysym.sym;size_t n=strlen(name_entry);
                if(key==SDLK_ESCAPE) {ff_wz_leave(&wz,&np);name_entry[0]=0;}
                else if(naming&&key==SDLK_BACKSPACE&&n) name_entry[n-1]=0;
                else if(naming&&(key==SDLK_RETURN||key==SDLK_KP_ENTER)) ff_wz_register(&wz,name_entry);
                continue;
            }
            if(wz_screen&&event.type==SDL_CONTROLLERBUTTONDOWN) {
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK) ff_wz_leave(&wz,&np);
                if(naming&&event.cbutton.button==SDL_CONTROLLER_BUTTON_START) ff_wz_register(&wz,name_entry);
                continue;
            }
            if(ranked_menu&&event.type==SDL_KEYDOWN&&!event.key.repeat) {
                SDL_Keycode key=event.key.keysym.sym;
                if(key==SDLK_ESCAPE) ranked_menu=false;
                else if(key==SDLK_UP) ranked_choice=(ranked_choice+2)%3;
                else if(key==SDLK_DOWN||key==SDLK_TAB) ranked_choice=(ranked_choice+1)%3;
                else if((key==SDLK_RETURN||key==SDLK_KP_ENTER)&&wz.online) {ranked_menu=false;ff_wz_queue(&wz,queue_ids[ranked_choice]);}
                continue;
            }
            if(ranked_menu&&event.type==SDL_CONTROLLERBUTTONDOWN) {
                int b=event.cbutton.button;
                if(b==SDL_CONTROLLER_BUTTON_BACK||b==SDL_CONTROLLER_BUTTON_B) ranked_menu=false;
                else if(b==SDL_CONTROLLER_BUTTON_DPAD_UP) ranked_choice=(ranked_choice+2)%3;
                else if(b==SDL_CONTROLLER_BUTTON_DPAD_DOWN) ranked_choice=(ranked_choice+1)%3;
                else if((b==SDL_CONTROLLER_BUTTON_A||b==SDL_CONTROLLER_BUTTON_START)&&wz.online) {ranked_menu=false;ff_wz_queue(&wz,queue_ids[ranked_choice]);}
                continue;
            }
            if(entering&&event.type==SDL_TEXTINPUT) {
                for(const char *c=event.text.text;*c;++c) {
                    char ch=(char)(*c>='a'&&*c<='z'?*c-32:*c);size_t n=strlen(entry);
                    if(n<sizeof(entry)-1&&((ch>='A'&&ch<='Z')||(ch>='0'&&ch<='9')||ch=='-'||ch=='.'||ch==':')) {entry[n]=ch;entry[n+1]=0;}
                }
                continue;
            }
            if(event.type==SDL_KEYDOWN&&!event.key.repeat&&entering) {
                SDL_Keycode key=event.key.keysym.sym;size_t n=strlen(entry);
                if(key==SDLK_ESCAPE) {entering=false;entry_error[0]=0;}
                else if(key==SDLK_BACKSPACE&&n) entry[n-1]=0;
                else if(key==SDLK_v&&(event.key.keysym.mod&KMOD_CTRL)) {
                    char *clip=SDL_GetClipboardText();
                    if(clip) {
                        for(const char *c=clip;*c&&strlen(entry)<sizeof(entry)-1;++c) {
                            char ch=(char)(*c>='a'&&*c<='z'?*c-32:*c);size_t m=strlen(entry);
                            if((ch>='A'&&ch<='Z')||(ch>='0'&&ch<='9')||ch=='-'||ch=='.'||ch==':') {entry[m]=ch;entry[m+1]=0;}
                        }
                        SDL_free(clip);
                    }
                } else if(key==SDLK_RETURN||key==SDLK_KP_ENTER) {
                    int local=seat_count(lobby.joined);
                    if(wz.online&&ff_wz_is_code(entry)) {ff_wz_join_code(&wz,entry,local?local:1);entering=false;entry_error[0]=0;}
                    else if(ff_np_join(&np,&arena,entry,local?local:1,!getenv("FF_NET_LAN_ONLY"))) {entering=false;entry_error[0]=0;}
                    else snprintf(entry_error,sizeof(entry_error),"%s",np.status);
                }
                continue;
            }
            if(event.type==SDL_KEYDOWN&&!event.key.repeat&&online) {
                SDL_Keycode key=event.key.keysym.sym;
                if(key==SDLK_F1) help=!help;
                else if(key==SDLK_ESCAPE) leave=true;
                else if(key==SDLK_RETURN||key==SDLK_KP_ENTER) start=true;
                else if(key==SDLK_TAB) mode_key=true;
                continue;
            }
            if(event.type==SDL_CONTROLLERBUTTONDOWN&&entering) {
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK) {entering=false;entry_error[0]=0;}
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_START) {
                    SDL_Event enter={0};enter.type=SDL_KEYDOWN;enter.key.keysym.sym=SDLK_RETURN;SDL_PushEvent(&enter);
                }
                continue;
            }
            if(event.type==SDL_CONTROLLERBUTTONDOWN&&online) {
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_START) {if(help) help=false;else start=true;}
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK) {if(help) help=false;else leave=true;}
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_A&&np.phase==FF_NP_ENDED) start=true;
                continue;
            }
            if(event.type==SDL_KEYDOWN&&!event.key.repeat) {
                SDL_Keycode key=event.key.keysym.sym;
                if(key==SDLK_F1) help=!help;
                else if(in_lobby&&key==SDLK_h) {
                    int local=seat_count(lobby.joined);
                    if(wz.online&&!getenv("FF_NET_LAN_ONLY")) ff_wz_host(&wz,local?local:1,lobby.mode);
                    else ff_np_host(&np,&arena,local?local:1,FF_NET_PORT,!getenv("FF_NET_LAN_ONLY"));
                    copied=false;copied_code[0]=0;
                }
                else if(in_lobby&&key==SDLK_r&&wz.available) ranked_menu=true;
                else if(in_lobby&&key==SDLK_j) {entering=true;entry[0]=0;entry_error[0]=0;}
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
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_BACK) {
                    if(help) help=false;
                    else if(!in_lobby) back=true;
                    else {
                        int local=seat_count(lobby.joined);
                        if(wz.online&&!getenv("FF_NET_LAN_ONLY")) ff_wz_host(&wz,local?local:1,lobby.mode);
                        else ff_np_host(&np,&arena,local?local:1,FF_NET_PORT,!getenv("FF_NET_LAN_ONLY"));
                        copied=false;copied_code[0]=0;
                    }
                }
                if(event.cbutton.button==SDL_CONTROLLER_BUTTON_RIGHTSHOULDER&&in_lobby&&wz.available&&!help) ranked_menu=true;
            }
        }
        if(online) {
            uint8_t keys[FF_PLAYERS];ff_input_read(&app.input,keys);
            for(int i=0;i<FF_PLAYERS;++i) {
                uint8_t pressed=keys[i]&(uint8_t)~online_previous[i];online_previous[i]=keys[i];
                if(i<np.local_count&&(pressed&FF_FLY)) mode_key=true;
            }
            if(np.phase==FF_NP_LOBBY) {
                ff_np_poll(&np);
                if(np.host&&mode_key&&!wz.ranked) {np.mode=np.mode==FF_TEAMS?FF_FFA:FF_TEAMS;ff_wz_mode_changed(&wz,np.mode);}
                if(np.host&&start) ff_np_start(&np,np.mode,0);
                if(np.host&&strcmp(copied_code,np.code)&&(np.have_public||!np.stun_until)) {
                    /* Hand the code straight to the chat the players use to arrange the match. */
                    copied=SDL_SetClipboardText(np.code)==0;snprintf(copied_code,sizeof(copied_code),"%s",np.code);
                    if(auto_play) printf("online code=%s\n",np.code),fflush(stdout);
                }
            }
            if(leave||(np.phase==FF_NP_ENDED&&start)) {if(np.virtual_net) ff_wz_leave(&wz,&np);else ff_np_close(&np);in_lobby=true;paused=help=false;ff_input_read(&app.input,lobby.previous);}
        } else if(entering||wz_screen||ranked_menu) {
        } else if(in_lobby&&!auto_play) {
            uint8_t keys[FF_PLAYERS];ff_input_read(&app.input,keys);
            if(!help) lobby_update(&lobby,&app.input,keys);
            if(lobby.arena!=arena_index) {
                if(choose_arena(&app,&arena,&base,&mods,lobby.arena,arena_name,sizeof(arena_name))) arena_index=lobby.arena;
                else {lobby.arena=0;arena_index=0;choose_arena(&app,&arena,&base,&mods,0,arena_name,sizeof(arena_name));}
            }
            if(start&&lobby_ready(&lobby)) {
                ff_game_setup(&game,&arena,(uint32_t)SDL_GetPerformanceCounter()|1u,lobby.joined,lobby.mode);
                in_lobby=paused=false;
            }
        } else if(back) {in_lobby=true;paused=false;ff_input_read(&app.input,lobby.previous);}
        uint64_t now=SDL_GetPerformanceCounter(),elapsed=now-previous;previous=now;
        if(elapsed>frequency/4) elapsed=frequency/4;
        accumulator+=elapsed*FF_HZ;
        if(auto_play) accumulator=frequency;
        if(playing_online&&np.phase==FF_NP_PLAYING) {
            /* Online the clock never stops: the others are still playing. */
            if(auto_play) accumulator=frequency;
            while(accumulator>=frequency) {
                uint8_t keys[FF_PLAYERS];ff_input_read(&app.input,keys);
                if(auto_play) for(int i=0;i<FF_PLAYERS;++i) {
                    int seat=ff_np_seat_of_local(&np,i);uint32_t t=np.rb.frame;
                    keys[i]=seat<0?0:(uint8_t)(((t/(90u+(unsigned)seat*20u))%2?FF_LEFT:FF_RIGHT)|(t%(29u+(unsigned)seat*6u)==0?FF_JUMP:0)|FF_FIRE|(t%(19u+(unsigned)seat)==0?FF_PUNCH:0));
                }
                unsigned sounds=ff_np_tick(&np,keys);accumulator-=frequency;
                if(app.audio) for(int i=0;i<FF_SOUNDS;++i) if((sounds&(1u<<i))&&app.sounds[i]) Mix_PlayChannel(-1,app.sounds[i],0);
                if(auto_play) break;
            }
            if(auto_play&&!wz.ranked&&ff_rb_settled(&np.rb)>=(uint32_t)ticks+FF_RB_CHECK) {
                uint32_t target=(uint32_t)ticks-(uint32_t)ticks%FF_RB_CHECK;unsigned slot=(target/FF_RB_CHECK)%16u;
                snprintf(online_result,sizeof(online_result),"online frame=%u state=%08x rollbacks=%u desync=%d",
                         np.rb.check_frame[slot],np.rb.check_hash[slot],np.rb.rollbacks,np.rb.desync!=UINT32_MAX);
                /* Keep the others supplied with our inputs before leaving; they may still quit first. */
                for(uint32_t until=SDL_GetTicks()+2000;SDL_GetTicks()<until;) {ff_wz_update(&wz,&np,&arena);ff_np_send(&np);SDL_Delay(10);}
                running=false;
            }
            if(auto_play) SDL_Delay(10);
            accumulator=auto_play?0:accumulator;
        } else if(online&&auto_play&&np.phase==FF_NP_LOBBY) {
            int n=0;for(int i=0;i<FF_PLAYERS;++i) n+=(np.seats>>i)&1u;
            static int lobby_frames;
            if(show_lobby&&++lobby_frames>=ticks) running=false;
            if(np.host&&n==players&&!wz.ranked) ff_np_start(&np,teams?FF_TEAMS:FF_FFA,4242);
            SDL_Delay(10);
        } else if(online&&auto_play&&np.phase==FF_NP_ENDED&&!np.finished) {fprintf(stderr,"online: %s\n",np.ended);result=1;goto cleanup;}
        if(paused||help||(in_lobby&&!auto_play)||online||entering||wz_screen||ranked_menu) accumulator=0;
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
        if(np.finished&&np.phase!=FF_NP_OFF) {draw(&app,&arena,&np.rb.state,false,false);draw_result(&app,&np,&wz);}
        else if(np.phase==FF_NP_PLAYING) {
            draw(&app,&arena,&np.rb.state,help,false);draw_net_overlay(&app,&np,&wz);
            static bool reported;
            if(np.rb.desync!=UINT32_MAX&&!reported) {reported=true;fprintf(stderr,"Online desync at frame %u\n",np.rb.desync);ff_fault("runtime");}
        }
        else if(np.phase!=FF_NP_OFF) {draw_online(&app,&np,copied,&wz);if(help) draw_help(&app);}
        else if(wz_screen) draw_warpzone(&app,&wz,name_entry,naming);
        else if(ranked_menu) draw_ranked_menu(&app,ranked_choice,&wz);
        else if(entering) draw_code_entry(&app,entry,entry_error);
        else if(in_lobby) {draw_lobby(&app,&lobby,&app.input,arena_name);if(help) draw_help(&app);}
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
        if(started) {
            uint32_t now=ff_net_ms();
            if(now-started>1500) fprintf(stderr,"slow start: data %ums, SDL and window %ums, images %ums, sounds %ums, rest %ums\n",
                stage[0]-started,stage[1]-stage[0],stage[2]-stage[1],stage[3]-stage[2],now-stage[3]);
            started=0;
        }
        SDL_RenderPresent(app.renderer);
        if(!auto_play) SDL_Delay(1);
    }
    if(online_result[0]) puts(online_result);
    else
    printf("ticks=%u state=%08x arena=%s\n",game.tick,ff_game_hash(&game),arena.imported?"local-import":"practice");
    result=0;goto cleanup;
fail:
    fprintf(stderr,"Runtime fault: %s\n",SDL_GetError());ff_fault("runtime");
cleanup:
    ff_np_close(&np);ff_wz_close(&wz);
    ff_input_close(&app.input);
    for(int i=0;i<FF_IMAGES;++i) if(app.images[i].texture) SDL_DestroyTexture(app.images[i].texture);
    for(int i=0;i<FF_SOUNDS;++i) if(app.sounds[i]) Mix_FreeChunk(app.sounds[i]);
    ff_mods_free(&mods);
    if(app.audio) Mix_CloseAudio();
    if(app.scene) SDL_DestroyTexture(app.scene);
    if(app.backdrop) SDL_DestroyTexture(app.backdrop);
    if(app.renderer) SDL_DestroyRenderer(app.renderer);
    if(app.window) SDL_DestroyWindow(app.window);
    IMG_Quit();SDL_Quit();return result;
}
