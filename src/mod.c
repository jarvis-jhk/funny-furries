#include "mod.h"
#include <ctype.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#endif

static FILE *open_utf8(const char *path,const char *mode) {
#ifdef _WIN32
    wchar_t wide[4096],wmode[8];
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,4096)<=0) return NULL;
    MultiByteToWideChar(CP_UTF8,0,mode,-1,wmode,8);
    return _wfopen(wide,wmode);
#else
    return fopen(path,mode);
#endif
}
/* A mod names files inside itself only: no absolute paths, no way up. */
static char *inside(const char *dir,const char *file) {
    if(!*file||file[0]=='/'||file[0]=='\\'||strchr(file,':')||strstr(file,"..")||strlen(file)>200) return NULL;
    size_t n=strlen(dir)+strlen(file)+2;char *path=malloc(n);
    if(path) snprintf(path,n,"%s/%s",dir,file);
    return path;
}
static void set_path(char **slot,char *path) {free(*slot);*slot=path;}
static void upper_name(char *out,size_t capacity,const char *in) {
    size_t n=0;
    for(;*in&&n+1<capacity;++in) {
        char c=(char)toupper((unsigned char)*in);
        if((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c==' '||c=='-') out[n++]=c;
        else if(c=='_') out[n++]='-';
    }
    out[n]=0;
}
static bool weapon_line(FF_Arena *a,char *line) {
    int slot;char *rest;
    if(sscanf(line,"weapon %d",&slot)!=1||slot<1||slot>=FF_WEAPONS) return false;
    rest=strchr(line+7,' ');if(!rest) return false;
    if(slot>a->rules.weapons+1) return false;   /* slots stay contiguous: they are pickup kinds */
    FF_Weapon w=a->weapons[slot];
    if(slot>a->rules.weapons) {
        w=(FF_Weapon){"WEAPON",60,0,100,6,0,0,10,10,20,0,0,0,0,1,0,1,-1,-1,-1};
    }
    for(char *token=strtok(rest," \t\r\n");token;token=strtok(NULL," \t\r\n")) {
        char *eq=strchr(token,'=');if(!eq) return false;
        *eq=0;const char *key=token,*value=eq+1;
        if(!strcmp(key,"name")) {memset(w.name,0,sizeof(w.name));upper_name(w.name,sizeof(w.name),value);if(!w.name[0]) return false;continue;}
        char *end;long v=strtol(value,&end,10);if(*end||end==value) return false;
        static const struct {const char *key;size_t offset;long lo,hi;} fields[]={
            {"speed",offsetof(FF_Weapon,speed),0,400},{"gravity",offsetof(FF_Weapon,gravity),-256,256},
            {"life",offsetof(FF_Weapon,life),1,3000},{"damage",offsetof(FF_Weapon,damage),0,100},
            {"knock",offsetof(FF_Weapon,knock),-100,100},{"lift",offsetof(FF_Weapon,lift),-100,100},
            {"cooldown",offsetof(FF_Weapon,cooldown),1,500},{"ammo",offsetof(FF_Weapon,ammo),1,999},
            {"max",offsetof(FF_Weapon,max_ammo),1,999},{"homing",offsetof(FF_Weapon,homing),0,4},
            {"blast",offsetof(FF_Weapon,blast),0,1},{"flame",offsetof(FF_Weapon,flame),0,20},
            {"bounces",offsetof(FF_Weapon,bounces),0,20},{"pellets",offsetof(FF_Weapon,pellets),1,8},
            {"spread",offsetof(FF_Weapon,spread),0,8},{"sound",offsetof(FF_Weapon,sound),0,FF_SOUNDS-1},
            {"shot",offsetof(FF_Weapon,shot_image),-1,FF_IMAGES-1},{"pickup",offsetof(FF_Weapon,pickup_image),-1,FF_IMAGES-1},
            {"hand",offsetof(FF_Weapon,hand_image),-1,FF_IMAGES-1},
        };
        bool known=false;
        for(size_t i=0;i<sizeof(fields)/sizeof(fields[0]);++i) if(!strcmp(key,fields[i].key)) {
            if(v<fields[i].lo||v>fields[i].hi) return false;
            *(int *)((char *)&w+fields[i].offset)=(int)v;known=true;
        }
        if(!known) return false;
    }
    if(w.max_ammo<w.ammo) w.max_ammo=w.ammo;
    a->weapons[slot]=w;if(slot>a->rules.weapons) a->rules.weapons=slot;
    return true;
}
bool ff_mod_apply(FF_Arena *a,FF_Mods *m,const char *dir,const char *name,char *error,unsigned capacity) {
    char path[4096];snprintf(path,sizeof(path),"%s/mod.ff",dir);
    FILE *f=open_utf8(path,"r");
    if(!f) {snprintf(error,capacity,"Mod %s has no mod.ff",name);return false;}
    char line[1024],file[256];int lines=0,n[4];bool ok=true;
    while(fgets(line,sizeof(line),f)) {
        ++lines;
        if(!strchr(line,'\n')&&!feof(f)) {ok=false;break;}
        line[strcspn(line,"\r\n")]=0;
        if(lines==1) {int version;ok=sscanf(line,"FFMOD %d",&version)==1&&version==1;if(!ok) break;continue;}
        if(!line[0]||line[0]=='#') continue;
        int got;
        if(sscanf(line,"image %d %255s%n",&n[0],file,&got)==2) {
            int extra=sscanf(line+got,"%d %d",&n[1],&n[2]);
            char *p=inside(dir,file);
            if(!p||n[0]<0||n[0]>=FF_MOD_IMAGES||(extra!=2&&extra!=EOF&&extra!=0)) {free(p);ok=false;break;}
            set_path(&m->image_path[n[0]],p);
            if(extra==2) {
                if(n[1]<-4096||n[1]>4096||n[2]<-4096||n[2]>4096) {ok=false;break;}
                a->hot_x[n[0]]=n[1];a->hot_y[n[0]]=n[2];m->center[n[0]]=false;
            } else m->center[n[0]]=n[0]>=FF_ORIGINAL_IMAGES;   /* replacements keep the original hot spot */
        } else if(sscanf(line,"sound %d %255s",&n[0],file)==2) {
            char *p=inside(dir,file);
            if(!p||n[0]<0||n[0]>=FF_SOUNDS) {free(p);ok=false;break;}
            set_path(&m->sound_path[n[0]],p);
        } else if(!strncmp(line,"weapon ",7)) {
            if(!weapon_line(a,line)) {ok=false;break;}
        } else if(sscanf(line,"rule lives %d",&n[0])==1) {
            if(n[0]<1||n[0]>99) {ok=false;break;} a->rules.lives=n[0];
        } else if(sscanf(line,"rule gravity %d",&n[0])==1) {
            if(n[0]<8||n[0]>256) {ok=false;break;} a->rules.gravity=n[0];
        } else if(sscanf(line,"rule jump %d",&n[0])==1) {
            if(n[0]<10||n[0]>120) {ok=false;break;} a->rules.jump=n[0];
        } else if(sscanf(line,"level %255s",file)==1) {
            char *p=inside(dir,file);
            if(!p||m->level_count==FF_MOD_LEVELS) {free(p);ok=false;break;}
            /* The menu shows a level by its own name line, read here so a broken level shows up now. */
            FILE *level=open_utf8(p,"r");char head[256]="",title[256]="";
            if(level) {
                while(fgets(head,sizeof(head),level)) if(sscanf(head,"name %255[^\r\n]",title)==1) break;
                fclose(level);
            }
            if(!level||!title[0]) {free(p);ok=false;break;}
            m->level_path[m->level_count]=p;
            upper_name(m->level_name[m->level_count],sizeof(m->level_name[0]),title);++m->level_count;
        } else {ok=false;break;}
    }
    fclose(f);
    if(!ok) {snprintf(error,capacity,"Mod %s: mod.ff line %d is not understood",name,lines);return false;}
    size_t used=strlen(m->names);
    if(used+strlen(name)+3<sizeof(m->names)) {
        if(used) strcat(m->names,", ");
        char upper[64];upper_name(upper,sizeof(upper),name);strcat(m->names,upper);
    }
    ++m->mod_count;return true;
}

static const char *const device_names[]={"","water","fan-left","fan-right","fan-up","spring-up","spring-down",
    "spring-left","spring-right","platform","wind-left","wind-right","wind-up"};
static int picture(FF_Mods *m,const char *dir,const char *file) {
    if(m->next_picture<FF_MOD_IMAGES) m->next_picture=FF_MOD_IMAGES;
    if(m->next_picture>=FF_IMAGES) return -1;
    char *p=inside(dir,file);if(!p) return -1;
    set_path(&m->image_path[m->next_picture],p);m->center[m->next_picture]=false;
    return m->next_picture++;
}
bool ff_level_apply(FF_Arena *a,FF_Mods *m,const char *path,FF_ImageReader reader,char *error,unsigned capacity) {
    char dir[4096];snprintf(dir,sizeof(dir),"%s",path);
    char *slash=strrchr(dir,'/');if(slash) *slash=0;else snprintf(dir,sizeof(dir),".");
    FILE *f=open_utf8(path,"r");
    if(!f) {snprintf(error,capacity,"Cannot open level %s",path);return false;}
    /* Devices take the original's look: the first of each kind is the template. */
    FF_Device templates[FF_WIND_UP+1]={{0}};
    for(int i=0;i<a->device_count;++i) if(!templates[a->devices[i].kind].kind) templates[a->devices[i].kind]=a->devices[i];
    memset(a->tiles,0,sizeof(a->tiles));memset(a->mask,0,sizeof(a->mask));
    a->spawn_count=a->layer_count=a->bonus_count=a->device_count=0;memset(a->paths,0,sizeof(a->paths));
    char line[1024],file[256],word[32];int lines=0,n[6];unsigned c[2];bool ok=true,scoreboard=false;
    while(fgets(line,sizeof(line),f)) {
        ++lines;
        if(!strchr(line,'\n')&&!feof(f)) {ok=false;break;}
        line[strcspn(line,"\r\n")]=0;
        if(lines==1) {int version;ok=sscanf(line,"FFLEVEL %d",&version)==1&&version==1;if(!ok) break;continue;}
        if(!line[0]||line[0]=='#'||!strncmp(line,"name ",5)) continue;
        if(!strcmp(line,"scoreboard")) {scoreboard=true;continue;}
        if(sscanf(line,"picture %255s %d %d",file,&n[0],&n[1])==3) {
            int id=picture(m,dir,file),w,h;uint8_t *rgba=NULL;
            if(id<0||!reader||!reader(m->image_path[id],&w,&h,&rgba)||a->layer_count==FF_LAYERS) {free(rgba);ok=false;break;}
            free(rgba);a->hot_x[id]=a->hot_y[id]=0;
            a->layers[a->layer_count++]=(FF_Layer){id,n[0],n[1],w,h,0,{0,0}};
        } else if(sscanf(line,"fill %x %d %d %d %d",&c[0],&n[0],&n[1],&n[2],&n[3])==5) {
            if(a->layer_count==FF_LAYERS||c[0]>0xffffff||n[2]<1||n[3]<1||n[2]>4096||n[3]>4096) {ok=false;break;}
            a->layers[a->layer_count++]=(FF_Layer){-1,n[0],n[1],n[2],n[3],2,{c[0],c[0]}};
        } else if(sscanf(line,"gradient %x %x %d %d %d %d",&c[0],&c[1],&n[0],&n[1],&n[2],&n[3])==6) {
            if(a->layer_count==FF_LAYERS||c[0]>0xffffff||c[1]>0xffffff||n[2]<1||n[3]<1||n[2]>4096||n[3]>4096) {ok=false;break;}
            a->layers[a->layer_count++]=(FF_Layer){-1,n[0],n[1],n[2],n[3],3,{c[0],c[1]}};
        } else if(sscanf(line,"layer %d %d %d %d %d %d %x %x",&n[0],&n[1],&n[2],&n[3],&n[4],&n[5],&c[0],&c[1])==8) {
            if(a->layer_count==FF_LAYERS||n[0]<-1||n[0]>=FF_IMAGES||n[3]<1||n[3]>4096||n[4]<1||n[4]>4096||n[5]<0||n[5]>4) {ok=false;break;}
            a->layers[a->layer_count++]=(FF_Layer){n[0],n[1],n[2],n[3],n[4],n[5],{c[0],c[1]}};
        } else if(sscanf(line,"collision %255s",file)==1) {
            /* Black is wall, blue a one-way platform top, everything else air. */
            int x0=0,y0=0;sscanf(line,"collision %*s %d %d",&x0,&y0);
            char *p=inside(dir,file);int w,h;uint8_t *rgba=NULL;
            if(!p||!reader||!reader(p,&w,&h,&rgba)) {free(p);free(rgba);ok=false;break;}
            for(int y=0;y<h;++y) for(int x=0;x<w;++x) {
                int xx=x0+x,yy=y0+y;if(xx<0||xx>=FF_W||yy<0||yy>=FF_H) continue;
                const uint8_t *px=rgba+((size_t)y*(size_t)w+(size_t)x)*4;
                if(px[3]<128) continue;
                if(px[0]<80&&px[1]<80&&px[2]<80) a->mask[yy][xx]=FF_SOLID;
                else if(px[2]>=160&&px[0]<96&&px[1]<96) a->mask[yy][xx]=FF_PLATFORM;
            }
            free(p);free(rgba);
        } else if(sscanf(line,"%31s %d %d %d %d",word,&n[0],&n[1],&n[2],&n[3])==5&&(!strcmp(word,"solid")||!strcmp(word,"platform"))) {
            int kind=!strcmp(word,"solid")?FF_SOLID:FF_PLATFORM;
            for(int y=n[1];y<n[1]+n[3];++y) for(int x=n[0];x<n[0]+n[2];++x)
                if(x>=0&&x<FF_W&&y>=0&&y<FF_H) a->mask[y][x]=(uint8_t)kind;
        } else if(sscanf(line,"spawn %d %d",&n[0],&n[1])==2) {
            if(a->spawn_count==FF_SPAWNS||n[0]<12||n[0]>788||n[1]<32||n[1]>560) {ok=false;break;}
            a->spawns[a->spawn_count++]=(FF_Point){n[0],n[1]};
        } else if(sscanf(line,"bonus %d %d",&n[0],&n[1])==2) {
            if(a->bonus_count==FF_SPAWNS||n[0]<0||n[0]>=FF_W||n[1]<0||n[1]>=560) {ok=false;break;}
            a->bonuses[a->bonus_count++]=(FF_Point){n[0],n[1]};
        } else if(sscanf(line,"moving %d %d %d %d %d",&n[0],&n[1],&n[2],&n[3],&n[4])==5) {
            FF_Device t=templates[FF_MOVING_PLATFORM];
            if(!t.kind) continue;   /* without the original's look (practice arena) a device is left out */
            if(a->device_count==FF_DEVICES||n[2]>n[0]||n[3]<n[0]||n[2]>=n[3]||n[2]<-4096||n[3]>4096||n[4]<1||n[4]>8) {ok=false;break;}
            a->paths[a->device_count]=(FF_Path){n[2],n[3],n[4],1};
            a->devices[a->device_count++]=(FF_Device){FF_MOVING_PLATFORM,n[0],n[1],t.w,t.h,t.image};
        } else if(sscanf(line,"place %31s %d %d",word,&n[0],&n[1])==3) {
            int kind=0;for(int k=1;k<=FF_WIND_UP;++k) if(!strcmp(word,device_names[k])) kind=k;
            if(!kind||kind==FF_MOVING_PLATFORM||a->device_count==FF_DEVICES||n[0]<-4096||n[0]>4096||n[1]<-4096||n[1]>4096) {ok=false;break;}
            FF_Device d={kind,n[0],n[1],0,0,-1};
            if(kind>=FF_WIND_LEFT) {
                if(sscanf(line,"place %*s %*d %*d %d %d",&n[2],&n[3])!=2||n[2]<1||n[2]>1024||n[3]<1||n[3]>1024) {ok=false;break;}
                d.w=n[2];d.h=n[3];
            } else {
                if(!templates[kind].kind) continue;
                d.w=templates[kind].w;d.h=templates[kind].h;d.image=templates[kind].image;
            }
            a->devices[a->device_count++]=d;
        } else {ok=false;break;}
    }
    fclose(f);
    if(ok&&a->spawn_count<2) {snprintf(error,capacity,"Level %s needs two spawn points",path);return false;}
    if(!ok) {snprintf(error,capacity,"Level %s: line %d is not understood",path,lines);return false;}
    /* The original two-player panel only where the level asks for it and has room. */
    a->hud.on=a->hud.on&&scoreboard&&a->hud.has_panel&&a->layer_count<FF_LAYERS;
    if(a->hud.on) a->layers[a->layer_count++]=a->hud.panel;
    a->imported=true;return true;
}
void ff_mods_free(FF_Mods *m) {
    for(int i=0;i<FF_IMAGES;++i) free(m->image_path[i]);
    for(int i=0;i<FF_SOUNDS;++i) free(m->sound_path[i]);
    for(int i=0;i<m->level_count;++i) free(m->level_path[i]);
    memset(m,0,sizeof(*m));
}

/* Just enough JSON for the launcher's lockfile: string values of flat keys. */
static const char *string_after(const char *p,const char *key,char *out,size_t capacity,const char *limit) {
    char quoted[64];snprintf(quoted,sizeof(quoted),"\"%s\"",key);
    const char *k=strstr(p,quoted);if(!k||(limit&&k>=limit)) return NULL;
    k=strchr(k+strlen(quoted),':');if(!k) return NULL;
    while(*++k==' '||*k=='\n'||*k=='\r'||*k=='\t') {}
    if(*k!='"') return NULL;
    size_t n=0;for(++k;*k&&*k!='"';++k) {if(*k=='\\'&&k[1]) ++k;if(n+1<capacity) out[n++]=*k;}
    out[n]=0;return *k?k+1:NULL;
}
static void warpzone_home(char *out,size_t capacity) {
    const char *h=getenv("WARPZONE_HOME");
    if(h&&*h) {snprintf(out,capacity,"%s",h);return;}
#ifdef _WIN32
    const char *a=getenv("APPDATA");snprintf(out,capacity,"%s/warpzone",a?a:".");
#else
    const char *x=getenv("XDG_DATA_HOME"),*home=getenv("HOME");
    if(x&&*x) snprintf(out,capacity,"%s/warpzone",x);
    else snprintf(out,capacity,"%s/.local/share/warpzone",home?home:".");
#endif
}
const char *ff_mods_active(void (*found)(const char *dir,const char *name,void *user),void *user) {
    static char hash[80];hash[0]=0;
    char root[4096],path[4200];warpzone_home(root,sizeof(root));
    snprintf(path,sizeof(path),"%s/mods/funny-furries/active.lock.json",root);
    FILE *f=open_utf8(path,"rb");if(!f) return hash;
    static char text[1<<20];size_t size=fread(text,1,sizeof(text)-1,f);fclose(f);text[size]=0;
    const char *order=strstr(text,"\"order\""),*mods=strstr(text,"\"mods\"");
    if(!order||!mods||!string_after(text,"hash",hash,sizeof(hash),NULL)) {hash[0]=0;return hash;}
    const char *p=strchr(order,'[');const char *end=p?strchr(p,']'):NULL;
    while(p&&end) {
        char name[64],version[64];
        const char *q=strchr(p,'"');if(!q||q>end) break;
        size_t n=0;for(++q;*q&&*q!='"'&&n+1<sizeof(name);++q) name[n++]=*q;
        name[n]=0;p=q+1;
        /* Find this mod's entry: the object whose name matches. */
        const char *entry=mods;char got[64];
        while((entry=string_after(entry,"name",got,sizeof(got),NULL))&&strcmp(got,name)) {}
        if(!entry||!string_after(entry,"version",version,sizeof(version),NULL)) continue;
        char dir[4400];snprintf(dir,sizeof(dir),"%s/mods/funny-furries/%s/%s/files",root,name,version);
        found(dir,name,user);
    }
    return hash;
}
