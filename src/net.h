#ifndef FF_NET_H
#define FF_NET_H
#include <stdint.h>
#include <stdbool.h>
/* IPv4 UDP for online play, plus the two outside helpers it needs: a public
 * STUN server to learn the address the internet sees, and the public ntfy.sh
 * relay over plain HTTP so a joining player can tell the host where to punch. */
#define FF_NET_PORT 27590
typedef struct { uint32_t ip; uint16_t port; } FF_Addr;   /* host byte order */
typedef struct { uint32_t due; FF_Addr to; int length; uint8_t data[512]; } FF_Delayed;
typedef struct {
    intptr_t fd; uint16_t port;
    /* FF_NET_LOSS / FF_NET_DELAY / FF_NET_JITTER simulate a bad line for tests. */
    int loss, delay, jitter; uint32_t rng;
    FF_Delayed queue[256]; int queued;
} FF_Udp;
typedef struct {
    intptr_t fd; int state; uint32_t deadline;
    char out[1024]; int out_length, sent;
    char in[8192]; int in_length;
} FF_Http;
bool ff_net_init(void);
uint32_t ff_net_ms(void);
bool ff_udp_open(FF_Udp *u, uint16_t port);          /* port 0 or taken: any free port */
void ff_udp_close(FF_Udp *u);
void ff_udp_send(FF_Udp *u, FF_Addr to, const void *data, int length);
int ff_udp_recv(FF_Udp *u, FF_Addr *from, void *data, int capacity);   /* -1: nothing */
bool ff_resolve(const char *host, uint16_t port, FF_Addr *out);
uint32_t ff_lan_ip(void);
bool ff_addr_equal(FF_Addr a, FF_Addr b);
void ff_addr_text(FF_Addr a, char *out, unsigned capacity);
bool ff_addr_parse(const char *text, FF_Addr *out);
void ff_stun_request(FF_Udp *u, FF_Addr server, const uint8_t id[12]);
bool ff_stun_response(const uint8_t *data, int length, const uint8_t id[12], FF_Addr *mapped);
/* A join code is the host's public address plus a session token, in a
 * 13-letter alphabet without look-alike letters, e.g. "8KQ2-M4XP-9ZTRA". */
void ff_code_make(FF_Addr host, uint16_t token, char out[20]);
bool ff_code_read(const char *text, FF_Addr *host, uint16_t *token);
void ff_http_start(FF_Http *h, FF_Addr server, const char *request);
int ff_http_poll(FF_Http *h);    /* 0 still running, 1 finished (h->in), -1 failed */
void ff_http_close(FF_Http *h);
#endif
