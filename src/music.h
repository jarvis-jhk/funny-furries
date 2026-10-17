#ifndef FF_MUSIC_H
#define FF_MUSIC_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
/* The original's two songs are General MIDI files. Rather than ship a sound font or
 * depend on a system synthesizer, a small synthesizer here plays them: one simple
 * timbre per instrument family and noise drums. It needs nothing but the file. */
typedef struct { uint32_t at; uint8_t status, a, b; } FF_MidiEvent;   /* at: samples from the start */
typedef struct {
    bool on, released; int channel, note, kind;
    float phase, step, gain, envelope, attack, decay, sustain, release, sweep, low, high;
    uint32_t age, noise;
} FF_Voice;
#define FF_VOICES 48
typedef struct {
    FF_MidiEvent *events; int count;
    uint32_t length;      /* samples, up to the song's last event */
    int rate;
    int next; uint32_t clock;
    int program[16]; float volume[16], expression[16], pan[16], bend[16];
    FF_Voice voices[FF_VOICES];
} FF_Song;
/* Reads a Standard MIDI File (format 0 or 1) from memory; false if it is not one. */
bool ff_song_parse(FF_Song *s, const uint8_t *data, size_t size, int rate);
bool ff_song_load(FF_Song *s, const char *path, int rate);
void ff_song_free(FF_Song *s);
void ff_song_restart(FF_Song *s);
/* Adds frames of interleaved stereo 16-bit sound to out; the song loops. */
void ff_song_render(FF_Song *s, int16_t *out, int frames, float volume);
#endif
