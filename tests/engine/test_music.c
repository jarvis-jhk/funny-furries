#include "music.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int checks;
#define CHECK(x) do { if(!(x)) {fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);} ++checks; } while(0)

/* A two-track file: 100 bpm; a piano A4 for one beat, a bass drum half a beat in, and a
 * second A4 ended by velocity 0 under running status. */
static const uint8_t song[]={
    'M','T','h','d',0,0,0,6, 0,1, 0,2, 0,96,
    'M','T','r','k',0,0,0,11, 0,0xFF,0x51,3,0x09,0x27,0xC0, 0,0xFF,0x2F,0,
    'M','T','r','k',0,0,0,26,
        0,0xC0,0, 0,0x90,69,100, 48,0x99,36,120, 48,0x80,69,0, 0,0x90,69,90, 96,69,0, 0,0xFF,0x2F,0,
};
static double pitch(const int16_t *buffer,int from,int to,int rate) {
    int crossings=0;
    for(int i=from+1;i<to;++i) if((buffer[2*(i-1)]<0)!=(buffer[2*i]<0)) ++crossings;
    return crossings/2.0/((double)(to-from)/rate);
}
int main(void) {
    FF_Song s;int rate=44100;
    CHECK(ff_song_parse(&s,song,sizeof(song),rate));
    CHECK(s.count==6);
    /* One beat at 100 bpm is 0.6 s: the note off and the second note fall on sample 26460. */
    CHECK(s.events[0].at==0&&s.events[0].status==0xC0);
    CHECK(s.events[2].status==0x99&&s.events[2].at==13230);
    CHECK(s.events[3].status==0x80&&s.events[3].at==26460);
    CHECK(s.events[5].status==0x90&&s.events[5].b==0&&s.events[5].at==52920);
    CHECK(s.length==52920u+(uint32_t)rate);
    int frames=rate;int16_t *buffer=calloc((size_t)frames*2,sizeof(int16_t));CHECK(buffer!=NULL);
    for(int at=0;at<frames;at+=512) ff_song_render(&s,buffer+2*at,frames-at<512?frames-at:512,1.0f);
    /* Before the drum: a 440 Hz tone, audible and not clipped. */
    double hz=pitch(buffer,2000,13000,rate);
    CHECK(hz>430&&hz<450);
    int peak=0;for(int i=0;i<frames*2;++i) {int v=abs(buffer[i]);if(v>peak) peak=v;}
    CHECK(peak>2000&&peak<32767);
    /* The song loops: past its end it starts again from the first event. */
    int16_t *rest=calloc((size_t)rate*2,sizeof(int16_t));CHECK(rest!=NULL);
    for(int k=0;k<2;++k) ff_song_render(&s,rest,rate,1.0f);
    CHECK(s.clock<s.length&&s.next>0&&s.next<s.count);
    /* Broken files are refused: truncated, wrong magic, SMPTE timing, a stray data byte. */
    FF_Song bad;
    CHECK(!ff_song_parse(&bad,song,sizeof(song)-5,rate));
    uint8_t copy[sizeof(song)];memcpy(copy,song,sizeof(song));copy[0]='X';
    CHECK(!ff_song_parse(&bad,copy,sizeof(copy),rate));
    memcpy(copy,song,sizeof(song));copy[12]=0xE7;
    CHECK(!ff_song_parse(&bad,copy,sizeof(copy),rate));
    memcpy(copy,song,sizeof(song));copy[22+11+8+1]=0x40;   /* first event without a status */
    CHECK(!ff_song_parse(&bad,copy,sizeof(copy),rate));
    ff_song_free(&s);free(buffer);free(rest);
    printf("%d music checks passed\n",checks);
    return 0;
}
