#ifndef FF_GAME_H
#define FF_GAME_H
#include <stdint.h>
#include <stdbool.h>
#define FF_W 800
#define FF_H 600
#define FF_HZ 50
#define FF_FP 256
#define FF_TILE 16
#define FF_COLS 50
#define FF_ROWS 38
#define FF_SHOTS 96
#define FF_PICKUPS 32
#define FF_SPAWNS 64
#define FF_LAYERS 2048
#define FF_IMAGES 1024
#define FF_ANIMS 16
#define FF_ANIM_FRAMES 32
#define FF_PARTS 5
#define FF_DEVICES 256
#define FF_HAZARDS 32
#define FF_BLASTS 32
#define FF_SOUNDS 8
#define FF_PLAYERS 4
/* winner: -1 while playing, a player index (free-for-all), FF_TEAM_WIN+team, or FF_DRAW. */
#define FF_TEAM_WIN 4
#define FF_DRAW 8

enum { FF_LEFT=1, FF_RIGHT=2, FF_JUMP=4, FF_PUNCH=8, FF_FIRE=16, FF_FLY=32 };
enum { FF_FISTS, FF_ICE, FF_FLAME, FF_ROCKET, FF_HEALTH, FF_FUEL };
enum { FF_FFA, FF_TEAMS };
enum { FF_SOLID=1, FF_PLATFORM=2 };
enum { FF_SOUND_PUNCH=1, FF_SOUND_ICE=2, FF_SOUND_FLAME=4, FF_SOUND_ROCKET=8, FF_SOUND_HIT=16, FF_SOUND_PICKUP=32, FF_SOUND_DEATH=64, FF_SOUND_BLAST=128 };
enum { FF_BOMB=1, FF_BOMB_WALK, FF_BOMB_FLY };
enum { FF_WATER=1, FF_FAN_LEFT, FF_FAN_RIGHT, FF_FAN_UP, FF_BOUNCE_UP,
       FF_BOUNCE_DOWN, FF_BOUNCE_LEFT, FF_BOUNCE_RIGHT, FF_MOVING_PLATFORM,
       FF_WIND_LEFT, FF_WIND_RIGHT, FF_WIND_UP };
typedef struct { int kind, x, y, w, h, image; } FF_Device;
typedef struct { int x, y; } FF_Point;
typedef struct { int x, y, w, h; } FF_Box;
typedef struct { int min_x, max_x, speed, direction; } FF_Path;
typedef struct { int image, x, y, w, h, kind; uint32_t color[2]; } FF_Layer;
/* speed is the original's animation speed: frames advance by speed/100 per tick;
 * 0 keeps the old fixed four ticks per frame. */
typedef struct { int count, speed, image[FF_ANIM_FRAMES]; } FF_Sequence;
/* The original two-player scoreboard: counters drawn over its panel image. */
enum { FF_HUD_LIVES, FF_HUD_SCORE, FF_HUD_AMMO, FF_HUD_FUEL, FF_HUD_ITEM, FF_HUD_FIELDS };
typedef struct {
    bool on; FF_Point field[2][FF_HUD_FIELDS]; int digits[11];
    FF_Sequence weapon[4]; int bar[3]; FF_Point bar_at; int bar_left, bar_right;
    uint32_t fuel_color; int fuel_width, fuel_height;
} FF_Hud;
typedef struct {
    uint8_t tiles[FF_ROWS][FF_COLS];
    uint8_t mask[FF_H][FF_W];
    FF_Point spawns[FF_SPAWNS]; int spawn_count;
    FF_Layer layers[FF_LAYERS]; int layer_count;
    int hot_x[FF_IMAGES], hot_y[FF_IMAGES];
    FF_Sequence sprites[2][FF_PARTS][FF_ANIMS][2];
    int pickup_images[6], shot_images[4];
    FF_Point muzzles[2][4][2];
    int sound_ids[FF_SOUNDS];
    FF_Point bonuses[FF_SPAWNS]; int bonus_count;
    FF_Sequence hazard_sprites[3][2], blast_sprite, fire_sprites[2];
    FF_Box blast_boxes[FF_ANIM_FRAMES];
    FF_Device devices[FF_DEVICES]; int device_count;
    FF_Path paths[FF_DEVICES];
    /* [kind][0] runs all the time, [kind][1] plays once when a device fires. */
    FF_Sequence device_sprites[FF_WIND_UP+1][2], pickup_sprites[6];
    FF_Hud hud;
    bool imported;
} FF_Arena;
typedef struct {
    int32_t x, y, vx, vy;
    int facing, health, lives, score, fuel, weapon, ammo;
    int grounded, cooldown, punch_ticks, invulnerable, burn_wait, respawn, bounce_wait;
    uint8_t previous;
    int active, team;
} FF_Player;
typedef struct { int32_t x, y, vx, vy; int kind, owner, life, direction, settled; } FF_Shot;
typedef struct { int x, y, kind, active, timer; } FF_Pickup;
typedef struct { int32_t x, y, vx, vy; int kind, life, grounded; } FF_Hazard;
typedef struct { int32_t x, y; int life; unsigned hit; } FF_Blast;
typedef struct {
    FF_Player players[FF_PLAYERS];
    FF_Shot shots[FF_SHOTS];
    FF_Pickup pickups[FF_PICKUPS];
    FF_Hazard hazards[FF_HAZARDS]; FF_Blast blasts[FF_BLASTS];
    int trap_wait, pickup_wait;
    uint32_t rng, tick;
    int winner, round_wait, mode;
    unsigned sounds;
    /* Tick a bouncer last fired; drawing only, so it stays out of the hash. */
    uint32_t device_hit[FF_DEVICES];
} FF_Game;
void ff_arena_practice(FF_Arena *a);
bool ff_arena_load(FF_Arena *a, const char *path, char *error, unsigned capacity);
/* seats is a bit mask of the players taking part; 2v2 pairs even and odd seats. */
void ff_game_setup(FF_Game *g, const FF_Arena *a, uint32_t seed, unsigned seats, int mode);
void ff_game_init(FF_Game *g, const FF_Arena *a, uint32_t seed);
void ff_game_tick(FF_Game *g, const FF_Arena *a, const uint8_t input[FF_PLAYERS]);
uint32_t ff_game_hash(const FF_Game *g);
FF_Point ff_device_position(const FF_Arena *a, int device, uint32_t tick);
/* Frame index of a sequence that has run for ticks (looping, or held on its last frame). */
int ff_sequence_frame(const FF_Sequence *s, uint32_t ticks, bool loop);
#endif
