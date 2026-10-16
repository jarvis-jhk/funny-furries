#ifndef FF_NETPLAY_H
#define FF_NETPLAY_H
#include "net.h"
#include "rollback.h"
/* An online match: one host, up to three guests, star topology. Guests send
 * their own seats' inputs to the host; the host forwards everyone's inputs to
 * everyone. Every machine runs the full rollback simulation itself. */
enum { FF_NP_OFF, FF_NP_LOBBY, FF_NP_PLAYING, FF_NP_ENDED };
#define FF_NP_PEERS 4
#define FF_NP_DELAY 2
typedef struct {
    bool used; FF_Addr addr; unsigned seats; int local_count;
    uint32_t heard, ack[FF_PLAYERS], frame, nonce; int advantage; bool started;
} FF_Peer;
typedef struct {
    int phase; bool host; char status[96];
    FF_Udp udp; uint16_t token; uint32_t arena_hash, nonce; const FF_Arena *arena;
    FF_Addr public_addr, lan_addr; bool have_public; char code[20], lan_text[32];
    FF_Peer peers[FF_NP_PEERS];      /* host: guests in 1..3; guest: peers[0] is the host */
    int me;                          /* own peer index: host 0 */
    int local_count; unsigned local_seats;
    unsigned seats; int mode; uint32_t seed;
    int owner[FF_PLAYERS];
    FF_Rollback rb; FF_Game start;
    uint32_t next_send, next_hello, stun_until, last_stall;
    uint8_t stun_id[12]; FF_Addr stun[2];
    /* NAT punching through the public ntfy.sh relay. */
    FF_Addr relay; bool relay_ok; char topic[40]; FF_Http http; bool http_busy; uint32_t next_poll; bool posted;
    FF_Addr punch[8]; uint32_t punch_until[8]; int punch_count;
    FF_Addr direct; bool direct_join;
    uint32_t stalled;               /* consecutive ticks waiting for the network */
    char ended[64];
    /* Over a virtual transport (Warpzone) the guest learns the host later, and
     * a ranked host seats each peer where the matchmaker's teams put it. */
    bool virtual_net, host_known;
    FF_Addr reserved_addr[FF_NP_PEERS]; unsigned reserved_seats[FF_NP_PEERS]; int reserved_count;
    /* A match with first_to set ends at the first fully confirmed frame where a
     * player (or team) has that many round wins; every machine finds the same
     * frame, so final_hash is the same everywhere. */
    int first_to; uint32_t scanned; bool finished; uint32_t final_frame, final_hash; int final_score[FF_PLAYERS];
} FF_Netplay;
uint32_t ff_arena_fingerprint(const FF_Arena *a);
bool ff_np_host(FF_Netplay *np, const FF_Arena *a, int local_count, uint16_t port, bool use_internet);
bool ff_np_join(FF_Netplay *np, const FF_Arena *a, const char *code, int local_count, bool use_internet);
bool ff_np_host_virtual(FF_Netplay *np, const FF_Arena *a, int local_count, FF_UdpHook hook, void *ctx);
bool ff_np_join_virtual(FF_Netplay *np, const FF_Arena *a, int local_count, FF_UdpHook hook, void *ctx);
void ff_np_virtual_host(FF_Netplay *np, FF_Addr host);          /* guest: the host is reachable now */
void ff_np_reserve(FF_Netplay *np, FF_Addr peer, unsigned seats); /* host: seats this peer gets */
void ff_np_set_local_seats(FF_Netplay *np, unsigned seats);       /* host, before anyone joined */
void ff_np_end(FF_Netplay *np, const char *why);
void ff_np_poll(FF_Netplay *np);                 /* call often: receives, resends, lobby */
bool ff_np_can_start(const FF_Netplay *np, int mode);
void ff_np_start(FF_Netplay *np, int mode, uint32_t seed);   /* host only */
/* One 50 Hz tick: local players' controls in, new sounds out. */
unsigned ff_np_tick(FF_Netplay *np, const uint8_t local[FF_PLAYERS]);
void ff_np_send(FF_Netplay *np);                 /* receive and resend without simulating */
void ff_np_close(FF_Netplay *np);
int ff_np_seat_of_local(const FF_Netplay *np, int local);
#endif
