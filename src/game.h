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

enum { FF_LEFT=1, FF_RIGHT=2, FF_JUMP=4, FF_PUNCH=8, FF_FIRE=16, FF_FLY=32 };
enum { FF_FISTS, FF_ICE, FF_FLAME, FF_ROCKET, FF_HEALTH, FF_FUEL };
enum { FF_SOLID=1, FF_PLATFORM=2 };
enum { FF_SOUND_PUNCH=1, FF_SOUND_ICE=2, FF_SOUND_FLAME=4, FF_SOUND_ROCKET=8, FF_SOUND_HIT=16, FF_SOUND_PICKUP=32, FF_SOUND_DEATH=64, FF_SOUND_BLAST=128 };
enum { FF_BOMB=1, FF_BOMB_WALK, FF_BOMB_FLY };
enum { FF_WATER=1, FF_FAN_LEFT, FF_FAN_RIGHT, FF_FAN_UP, FF_BOUNCE_UP,
       FF_BOUNCE_DOWN, FF_BOUNCE_LEFT, FF_BOUNCE_RIGHT, FF_MOVING_PLATFORM,
       FF_WIND_LEFT, FF_WIND_RIGHT, FF_WIND_UP };
typedef struct { int kind, x, y, w, h, image; } FF_Device;
typedef struct { int x, y; } FF_Point;
typedef struct { int min_x, max_x, speed, direction; } FF_Path;
typedef struct { int image, x, y, w, h, kind; uint32_t color[2]; } FF_Layer;
typedef struct { int count, image[FF_ANIM_FRAMES]; } FF_Sequence;
typedef struct {
    uint8_t tiles[FF_ROWS][FF_COLS];
    uint8_t mask[FF_H][FF_W];
    FF_Point spawns[FF_SPAWNS]; int spawn_count;
    FF_Layer layers[FF_LAYERS]; int layer_count;
    int hot_x[FF_IMAGES], hot_y[FF_IMAGES];
    FF_Sequence sprites[2][FF_PARTS][FF_ANIMS][2];
    int pickup_images[6], shot_images[4];
    int sound_ids[FF_SOUNDS];
    FF_Point bonuses[FF_SPAWNS]; int bonus_count;
    FF_Sequence hazard_sprites[3][2], blast_sprite;
    FF_Device devices[FF_DEVICES]; int device_count;
    FF_Path paths[FF_DEVICES];
    bool imported;
} FF_Arena;
typedef struct {
    int32_t x, y, vx, vy;
    int facing, health, lives, score, fuel, weapon, ammo;
    int grounded, cooldown, punch_ticks, invulnerable, frozen, respawn, swim_wait, bounce_wait;
    uint8_t previous;
} FF_Player;
typedef struct { int32_t x, y, vx, vy; int kind, owner, life, direction; } FF_Shot;
typedef struct { int x, y, kind, active, timer; } FF_Pickup;
typedef struct { int32_t x, y, vx, vy; int kind, life, grounded; } FF_Hazard;
typedef struct { int32_t x, y; int life; unsigned hit; } FF_Blast;
typedef struct {
    FF_Player players[2];
    FF_Shot shots[FF_SHOTS];
    FF_Pickup pickups[FF_PICKUPS];
    FF_Hazard hazards[FF_HAZARDS]; FF_Blast blasts[FF_BLASTS];
    int trap_wait, pickup_wait;
    uint32_t rng, tick;
    int winner, round_wait;
    unsigned sounds;
} FF_Game;
void ff_arena_practice(FF_Arena *a);
bool ff_arena_load(FF_Arena *a, const char *path, char *error, unsigned capacity);
void ff_game_init(FF_Game *g, const FF_Arena *a, uint32_t seed);
void ff_game_tick(FF_Game *g, const FF_Arena *a, const uint8_t input[2]);
uint32_t ff_game_hash(const FF_Game *g);
FF_Point ff_device_position(const FF_Arena *a, int device, uint32_t tick);
#endif
