#include "music.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#endif

enum { MAX_EVENTS=200000, MAX_TEMPOS=4096, MAX_FILE=4*1024*1024 };
typedef struct { uint32_t tick; int order; uint8_t status, a, b; } Raw;
typedef struct { uint32_t tick, tempo; } Tempo;

static bool varlen(const uint8_t *d,size_t end,size_t *p,uint32_t *value) {
    uint32_t v=0;
    for(int i=0;i<4;++i) {
        if(*p>=end) return false;
        uint8_t c=d[(*p)++];v=(v<<7)|(c&127u);
        if(!(c&128)) {*value=v;return true;}
    }
    return false;
}
static uint32_t be32(const uint8_t *d) {return (uint32_t)d[0]<<24|(uint32_t)d[1]<<16|(uint32_t)d[2]<<8|d[3];}
static int raw_order(const void *x,const void *y) {
    const Raw *a=x,*b=y;
    if(a->tick!=b->tick) return a->tick<b->tick?-1:1;
    return a->order<b->order?-1:a->order>b->order;
}
static int tempo_order(const void *x,const void *y) {
    const Tempo *a=x,*b=y;return a->tick<b->tick?-1:a->tick>b->tick;
}
bool ff_song_parse(FF_Song *s,const uint8_t *d,size_t size,int rate) {
    memset(s,0,sizeof(*s));
    if(size<14||memcmp(d,"MThd",4)||be32(d+4)<6||rate<8000) return false;
    int format=d[8]<<8|d[9],tracks=d[10]<<8|d[11],division=d[12]<<8|d[13];
    if(format>1||tracks<1||division<=0||division&0x8000) return false;
    Raw *raw=malloc(sizeof(Raw)*MAX_EVENTS);Tempo *tempos=malloc(sizeof(Tempo)*MAX_TEMPOS);
    int count=0,tempo_count=0;bool ok=raw&&tempos;
    size_t p=8+be32(d+4);
    for(int t=0;ok&&t<tracks;++t) {
        if(p+8>size||memcmp(d+p,"MTrk",4)) {ok=false;break;}
        size_t end=p+8+be32(d+p+4);p+=8;
        if(end>size) {ok=false;break;}
        uint32_t tick=0;uint8_t running=0;
        while(ok&&p<end) {
            uint32_t delta;if(!varlen(d,end,&p,&delta)) {ok=false;break;}
            tick+=delta;
            if(p>=end) {ok=false;break;}
            uint8_t status=d[p];
            if(status&0x80) ++p;else if(running) status=running;else {ok=false;break;}
            if(status==0xFF) {
                uint32_t length;if(p>=end) {ok=false;break;}
                uint8_t type=d[p++];
                if(!varlen(d,end,&p,&length)||length>end-p) {ok=false;break;}
                if(type==0x51&&length==3&&tempo_count<MAX_TEMPOS) tempos[tempo_count++]=(Tempo){tick,(uint32_t)d[p]<<16|(uint32_t)d[p+1]<<8|d[p+2]};
                if(type==0x2F) {p=end;break;}
                p+=length;continue;
            }
            if(status==0xF0||status==0xF7) {
                uint32_t length;if(!varlen(d,end,&p,&length)||length>end-p) {ok=false;break;}
                p+=length;continue;
            }
            if(status>=0xF0) {ok=false;break;}
            running=status;
            int need=(status&0xF0)==0xC0||(status&0xF0)==0xD0?1:2;
            if(p+(size_t)need>end) {ok=false;break;}
            uint8_t a=d[p]&127,b=need>1?d[p+1]&127:0;p+=(size_t)need;
            if(count==MAX_EVENTS) {ok=false;break;}
            raw[count]=(Raw){tick,count,status,a,b};++count;
        }
        p=end;
    }
    if(ok&&count) {
        qsort(raw,(size_t)count,sizeof(Raw),raw_order);
        qsort(tempos,(size_t)tempo_count,sizeof(Tempo),tempo_order);
        s->events=malloc(sizeof(FF_MidiEvent)*(size_t)count);ok=s->events!=NULL;
        /* Ticks become samples along the tempo map; a song without one runs at 120 bpm. */
        double samples=0;uint32_t last=0,tempo=500000;int next_tempo=0;
        for(int i=0;ok&&i<count;++i) {
            while(next_tempo<tempo_count&&tempos[next_tempo].tick<=raw[i].tick) {
                samples+=(double)(tempos[next_tempo].tick-last)*tempo/1e6/division*rate;
                last=tempos[next_tempo].tick;tempo=tempos[next_tempo].tempo?tempos[next_tempo].tempo:tempo;++next_tempo;
            }
            double at=samples+(double)(raw[i].tick-last)*tempo/1e6/division*rate;
            if(at>4e9) {ok=false;break;}
            s->events[i]=(FF_MidiEvent){(uint32_t)at,raw[i].status,raw[i].a,raw[i].b};
        }
        if(ok) {s->count=count;s->length=s->events[count-1].at+(uint32_t)rate;}
    } else ok=false;
    free(raw);free(tempos);
    if(!ok) {free(s->events);memset(s,0,sizeof(*s));return false;}
    s->rate=rate;ff_song_restart(s);
    return true;
}
bool ff_song_load(FF_Song *s,const char *path,int rate) {
    memset(s,0,sizeof(*s));
#ifdef _WIN32
    wchar_t wide[4096];FILE *f=NULL;
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,4096)>0) f=_wfopen(wide,L"rb");
#else
    FILE *f=fopen(path,"rb");
#endif
    if(!f) return false;
    uint8_t *data=malloc(MAX_FILE);size_t size=data?fread(data,1,MAX_FILE,f):0;
    fclose(f);
    bool ok=data&&size<MAX_FILE&&ff_song_parse(s,data,size,rate);
    free(data);return ok;
}
void ff_song_free(FF_Song *s) {free(s->events);memset(s,0,sizeof(*s));}
void ff_song_restart(FF_Song *s) {
    s->next=0;s->clock=0;memset(s->voices,0,sizeof(s->voices));
    for(int c=0;c<16;++c) {s->program[c]=0;s->volume[c]=100/127.0f;s->expression[c]=1;s->pan[c]=0.5f;s->bend[c]=0;}
}

/* Timbres: the wave, attack and decay time in seconds, sustain level, release time
 * and a low-pass amount. One per General MIDI family of eight programs. */
enum { SINE, TRIANGLE, SQUARE, SAW, PULSE, NOISE };
typedef struct { int wave; float attack, decay, sustain, release, smooth; } Timbre;
static const Timbre family[16]={
    {TRIANGLE,0.003f,0.9f,0.15f,0.15f,0.5f},   /* piano */
    {SINE,0.002f,0.5f,0.0f,0.3f,0.0f},         /* chromatic percussion */
    {SQUARE,0.01f,1.0f,0.8f,0.08f,0.75f},      /* organ */
    {SAW,0.003f,0.6f,0.1f,0.12f,0.7f},         /* guitar */
    {TRIANGLE,0.005f,1.2f,0.5f,0.08f,0.3f},    /* bass */
    {SAW,0.08f,1.0f,0.8f,0.25f,0.8f},          /* strings */
    {SAW,0.06f,1.0f,0.8f,0.3f,0.8f},           /* ensemble */
    {SAW,0.03f,1.0f,0.75f,0.12f,0.65f},        /* brass */
    {PULSE,0.02f,1.0f,0.8f,0.1f,0.7f},         /* reed */
    {SINE,0.03f,1.0f,0.85f,0.12f,0.0f},        /* pipe */
    {SQUARE,0.005f,1.0f,0.7f,0.1f,0.6f},       /* synth lead */
    {SAW,0.2f,1.5f,0.8f,0.5f,0.85f},           /* synth pad */
    {SINE,0.05f,1.5f,0.6f,0.4f,0.0f},          /* synth effects */
    {SAW,0.002f,0.4f,0.0f,0.15f,0.6f},         /* ethnic: plucked */
    {SINE,0.001f,0.25f,0.0f,0.1f,0.0f},        /* percussive */
    {NOISE,0.01f,0.5f,0.2f,0.2f,0.8f},         /* sound effects */
};
/* Drum kinds on channel 10, by sound: frequency, decay time, how much is noise. */
typedef struct { float freq, sweep, decay, noise, hiss; } Drum;
static Drum drum(int note) {
    switch(note) {
    case 35: case 36: return (Drum){150,0.4f,0.25f,0,0};          /* bass drum */
    case 38: case 40: return (Drum){190,0.8f,0.14f,0.75f,0};      /* snare */
    case 37: case 39: return (Drum){400,1,0.06f,0.9f,0.5f};       /* stick, clap */
    case 42: case 44: return (Drum){0,1,0.04f,1,1};               /* closed hi-hat */
    case 46: return (Drum){0,1,0.25f,1,1};                        /* open hi-hat */
    case 49: case 52: case 55: case 57: return (Drum){0,1,0.9f,1,0.9f};   /* crash */
    case 51: case 53: case 59: return (Drum){0,1,0.5f,1,1};       /* ride */
    case 41: case 43: case 45: case 47: case 48: case 50:         /* toms */
        return (Drum){70+(note-41)*14.0f,0.7f,0.3f,0.1f,0};
    case 56: return (Drum){560,1,0.12f,0,0};                      /* cowbell */
    case 60: case 61: case 62: case 63: case 64: return (Drum){180+(64-note)*45.0f,0.95f,0.12f,0.1f,0};   /* bongos, congas */
    case 67: case 68: return (Drum){note==67?900:700,1,0.15f,0,0};   /* agogo */
    case 69: case 70: case 82: return (Drum){0,1,0.05f,1,1};      /* cabasa, maracas, shaker */
    default: return (Drum){0,1,0.1f,1,0.7f};
    }
}
static float frequency(int note,float bend) {return 440.0f*powf(2.0f,((float)note-69.0f+bend)/12.0f);}
static float per_sample(float seconds,int rate) {
    /* The factor that shrinks a level to a thousandth over the given time. */
    return seconds<=0?0:powf(0.001f,1.0f/(seconds*(float)rate));
}
static void note_on(FF_Song *s,int channel,int note,int velocity) {
    FF_Voice *v=NULL;uint32_t oldest=0;
    for(int i=0;i<FF_VOICES;++i) if(!s->voices[i].on) {v=&s->voices[i];break;}
    if(!v) for(int i=0;i<FF_VOICES;++i) {
        FF_Voice *c=&s->voices[i];uint32_t age=c->age+(c->released?1u<<30:0);
        if(!v||age>oldest) {v=c;oldest=age;}
    }
    float gain=(float)velocity/127.0f;
    *v=(FF_Voice){true,false,channel,note,0,0,0,gain*gain,0,0,0,0,0,1,0,0,0,(uint32_t)(note*7919+velocity*31+1)};
    if(channel==9) {
        Drum k=drum(note);
        v->kind=-1;v->step=k.freq/(float)s->rate;v->sweep=powf(k.sweep,1.0f/(0.1f*(float)s->rate));
        v->attack=1;v->decay=per_sample(k.decay,s->rate);v->sustain=0;v->release=v->decay;
        v->low=k.noise;v->high=k.hiss;v->envelope=1;v->gain*=1.1f;
    } else {
        const Timbre *t=&family[(s->program[channel]>>3)&15];
        v->kind=(s->program[channel]>>3)&15;v->step=frequency(note,s->bend[channel])/(float)s->rate;
        v->attack=1.0f/(t->attack*(float)s->rate+1);v->decay=per_sample(t->decay,s->rate);
        v->sustain=t->sustain;v->release=per_sample(t->release,s->rate);
    }
}
static void note_off(FF_Song *s,int channel,int note) {
    for(int i=0;i<FF_VOICES;++i) {
        FF_Voice *v=&s->voices[i];
        if(v->on&&!v->released&&v->channel==channel&&v->note==note&&channel!=9) v->released=true;
    }
}
static void event(FF_Song *s,const FF_MidiEvent *e) {
    int channel=e->status&15;
    switch(e->status&0xF0) {
    case 0x90: if(e->b) note_on(s,channel,e->a,e->b);else note_off(s,channel,e->a);break;   /* velocity 0 is a note off */
    case 0x80: note_off(s,channel,e->a);break;
    case 0xC0: s->program[channel]=e->a;break;
    case 0xB0:
        if(e->a==7) s->volume[channel]=e->b/127.0f;
        else if(e->a==11) s->expression[channel]=e->b/127.0f;
        else if(e->a==10) s->pan[channel]=e->b/127.0f;
        else if(e->a==120||e->a==123) for(int i=0;i<FF_VOICES;++i) if(s->voices[i].channel==channel) s->voices[i].released=true;
        break;
    case 0xE0: {
        s->bend[channel]=(float)(((int)e->b<<7|e->a)-8192)/8192.0f*2.0f;
        for(int i=0;i<FF_VOICES;++i) {
            FF_Voice *v=&s->voices[i];
            if(v->on&&v->channel==channel&&channel!=9) v->step=frequency(v->note,s->bend[channel])/(float)s->rate;
        }
        break;
    }
    default: break;
    }
}
static float noise(FF_Voice *v) {
    v->noise^=v->noise<<13;v->noise^=v->noise>>17;v->noise^=v->noise<<5;
    return (float)(v->noise&0xFFFF)/32768.0f-1.0f;
}
static float voice_sample(FF_Voice *v) {
    float out;
    if(v->kind<0) {
        /* A drum: a falling tone, noise, and noise with its lows taken out (hiss). */
        float tone=sinf(v->phase*6.2831853f);
        v->phase+=v->step;if(v->phase>=1) v->phase-=1;
        v->step*=v->sweep>0?v->sweep:1;
        float n=noise(v),smooth=v->sustain=v->sustain*0.6f+n*0.4f;
        float hiss=n-smooth;
        out=tone*(1-v->low)+(n*(1-v->high)+hiss*1.6f*v->high)*v->low;
        v->envelope*=v->decay;
    } else {
        const Timbre *t=&family[v->kind];
        float ph=v->phase;
        switch(t->wave) {
        case SINE: out=sinf(ph*6.2831853f);break;
        case TRIANGLE: out=ph<0.5f?4*ph-1:3-4*ph;break;
        case SQUARE: out=ph<0.5f?0.7f:-0.7f;break;
        case SAW: out=(2*ph-1)*0.8f;break;
        case PULSE: out=ph<0.25f?0.7f:-0.4f;break;
        default: out=noise(v)*0.5f;break;
        }
        v->phase+=v->step;if(v->phase>=1) v->phase-=1;
        /* A one-pole low-pass rounds off the harsh edges of the simple waves. */
        v->low=v->low*t->smooth+out*(1-t->smooth);out=v->low;
        if(v->released) v->envelope*=v->release;
        else if(v->age==0||v->high<1) {v->high+=v->attack;if(v->high>1) v->high=1;v->envelope=v->high;}
        else v->envelope=v->sustain+(v->envelope-v->sustain)*v->decay;
    }
    ++v->age;
    if(v->age>8&&v->envelope<0.0005f) v->on=false;
    return out*v->envelope*v->gain;
}
void ff_song_render(FF_Song *s,int16_t *out,int frames,float volume) {
    if(!s->count) return;
    for(int f=0;f<frames;++f) {
        while(s->next<s->count&&s->events[s->next].at<=s->clock) event(s,&s->events[s->next++]);
        if(++s->clock>=s->length) ff_song_restart(s);
        float left=0,right=0;
        for(int i=0;i<FF_VOICES;++i) {
            FF_Voice *v=&s->voices[i];if(!v->on) continue;
            float level=voice_sample(v)*s->volume[v->channel]*s->expression[v->channel];
            float pan=s->pan[v->channel];
            left+=level*(1-pan)*1.4f;right+=level*pan*1.4f;
        }
        int l=(int)out[2*f]+(int)(left*volume*9000),r=(int)out[2*f+1]+(int)(right*volume*9000);
        out[2*f]=(int16_t)(l<-32768?-32768:l>32767?32767:l);
        out[2*f+1]=(int16_t)(r<-32768?-32768:r>32767?32767:r);
    }
}
