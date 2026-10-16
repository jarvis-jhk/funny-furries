#ifndef FF_ROLLBACK_H
#define FF_ROLLBACK_H
#include "game.h"
/* Rollback over the deterministic tick: every machine simulates every seat,
 * predicts a remote seat as "still holding what it held last", and when the
 * real input arrives and differs, restores the snapshot of that frame and
 * simulates forward again. No sockets here, so tests can drive it directly. */
#define FF_RB_RING 128
#define FF_RB_PREDICT 12
#define FF_RB_MAX_DELAY 8
#define FF_RB_CHECK 32
typedef struct {
    FF_Game state;
    uint32_t frame;                      /* frames simulated; state is the state before frame `frame` */
    uint32_t confirmed[FF_PLAYERS];      /* inputs 0..confirmed-1 of a seat are known for certain */
    uint8_t input[FF_RB_RING][FF_PLAYERS];
    uint8_t used[FF_RB_RING][FF_PLAYERS];
    FF_Game snap[FF_RB_RING];
    uint32_t rollback_to;                /* earliest frame simulated with a wrong guess, or UINT32_MAX */
    unsigned seats, local;               /* seats in the match, seats this machine owns */
    int delay;
    uint32_t sounded;                    /* frames whose sounds were already played */
    uint32_t next_check, check_frame[16], check_hash[16];
    uint32_t desync;                     /* frame of a checksum mismatch, or UINT32_MAX */
    unsigned rollbacks, resimulated;
} FF_Rollback;
void ff_rb_init(FF_Rollback *rb, const FF_Game *start, unsigned seats, unsigned local, int delay);
/* Known input of the earliest unconfirmed frame of one seat; false if it is
 * not the next one (older duplicates are ignored, gaps are refused). */
bool ff_rb_input(FF_Rollback *rb, int seat, uint32_t frame, uint8_t keys);
/* Lets local seats' current controls take effect `delay` frames from now. */
void ff_rb_local(FF_Rollback *rb, const uint8_t keys[FF_PLAYERS]);
/* Repairs mispredictions, then simulates one frame unless that would guess
 * more than FF_RB_PREDICT frames ahead of the slowest seat. Returns sounds of
 * new frames in *sounds. False means: wait for the network. */
bool ff_rb_advance(FF_Rollback *rb, const FF_Arena *a, unsigned *sounds);
uint32_t ff_rb_settled(const FF_Rollback *rb);  /* frames every seat confirmed */
bool ff_rb_can_take_local(const FF_Rollback *rb);
/* Latest checksum of a fully confirmed frame, to send to the other side. */
bool ff_rb_last_check(const FF_Rollback *rb, uint32_t *frame, uint32_t *hash);
void ff_rb_remote_check(FF_Rollback *rb, uint32_t frame, uint32_t hash);
#endif
