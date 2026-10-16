#ifndef FF_WZ_H
#define FF_WZ_H
#include "netplay.h"
/* Warpzone (github.com/jarvis-jhk/warpzone): accounts, rooms with join codes,
 * NAT traversal with a relay fallback, and ranked queues. Our rollback netplay
 * runs unchanged on top of it: its datagrams travel as Warpzone peer data.
 * Built without libwarpzone, every call is a no-op and `available` is false,
 * so the game falls back to its own join codes. */
#define FF_WZ_PEERS 8
#define FF_RANKED_WINS 3
enum { FF_WZ_NONE, FF_WZ_HOST, FF_WZ_JOIN_CODE, FF_WZ_QUEUE };
typedef struct { bool used, connected, relayed; uint32_t peer; int64_t account; char name[20]; } FF_WzPeer;
typedef struct {
    void *client; bool available, online, need_name, has_account;
    int64_t account; char username[20]; uint32_t opened_ms, login_ms;
    char status[96], error[96];
    int pending; char pending_arg[16]; int local_count, mode;   /* waiting for a name or the login */
    /* busy: a request runs (or failed) and there is no room yet */
    bool busy, in_room, host, hosting; char code[16], room[48];
    FF_WzPeer peers[FF_WZ_PEERS];
    /* Ranked: the queue, the match the matchmaker made, and its teams by name. */
    char queue[16]; bool queued, queue_confirmed; int waiting;
    bool ranked; char match_id[40]; int teams, team_size; char team_name[FF_PLAYERS][2][20];
    struct { int64_t account; char name[20]; } roster[FF_PLAYERS]; int roster_count;
    bool reported; char match_state[16];
    const FF_Arena *arena; bool started_sent;
} FF_Wz;
bool ff_wz_open(FF_Wz *wz, const char *version);
void ff_wz_close(FF_Wz *wz);
/* --warpzone-join/--warpzone-host: 1 joining, 2 open the host screen, 0 nothing. */
int ff_wz_launch(FF_Wz *wz, int argc, char **argv);
void ff_wz_register(FF_Wz *wz, const char *name);
/* Each of these asks for a name first if this device has none. */
void ff_wz_host(FF_Wz *wz, int local_count, int mode);
void ff_wz_join_code(FF_Wz *wz, const char *code, int local_count);
void ff_wz_queue(FF_Wz *wz, const char *queue);
void ff_wz_leave(FF_Wz *wz, FF_Netplay *np);
/* Every frame: drives the room, starts/feeds netplay, starts ranked matches
 * and reports their result. */
void ff_wz_update(FF_Wz *wz, FF_Netplay *np, const FF_Arena *arena);
void ff_wz_mode_changed(FF_Wz *wz, int mode);
void ff_wz_match_started(FF_Wz *wz, FF_Netplay *np);
/* "NAME 34 MS" or "NAME 80 MS RELAYED" for the n-th connected peer, false past the last. */
bool ff_wz_peer_line(FF_Wz *wz, int n, char *out, unsigned capacity);
bool ff_wz_is_code(const char *text);
bool ff_wz_seat_name(const FF_Wz *wz, int seat, char *out, unsigned capacity);   /* ranked player names */
#endif
