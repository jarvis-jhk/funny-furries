#ifndef FF_MOD_H
#define FF_MOD_H
#include "game.h"
/* Mods are data only: a directory with mod.ff (images, sounds, weapons, rules)
 * and level files drawn as PNG pictures. Nothing in a mod runs, so every machine
 * that loads the same mods simulates exactly the same game. docs/MODDING.md. */
#define FF_MOD_LEVELS 32
#define FF_MOD_IMAGES 1536   /* mod.ff ids are 1024-1535; levels number their pictures from here */
typedef struct {
    char *image_path[FF_IMAGES]; bool center[FF_IMAGES];
    char *sound_path[FF_SOUNDS];
    int level_count; char *level_path[FF_MOD_LEVELS]; char level_name[FF_MOD_LEVELS][32];
    int mod_count; char names[512];   /* "SNOWBALL-FIGHT, MIDNIGHT-PEAKS" for the menu */
    int next_picture;
} FF_Mods;
/* Decodes a PNG to RGBA (malloc'd); supplied by the renderer, NULL in pure tests. */
typedef bool (*FF_ImageReader)(const char *path, int *w, int *h, uint8_t **rgba);
/* Apply one mod directory on top of the arena; its levels are only listed. */
bool ff_mod_apply(FF_Arena *a, FF_Mods *m, const char *dir, const char *name, char *error, unsigned capacity);
/* Replace the arena's level (scenery, collision, spawns, devices) with a level file. */
bool ff_level_apply(FF_Arena *a, FF_Mods *m, const char *path, FF_ImageReader reader, char *error, unsigned capacity);
void ff_mods_free(FF_Mods *m);
/* The Warpzone launcher's active mod set for this game, in load order:
 * calls found(dir, name) for each installed mod. Returns the lockfile hash or "". */
const char *ff_mods_active(void (*found)(const char *dir, const char *name, void *user), void *user);
#endif
