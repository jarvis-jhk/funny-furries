# Modding Funny Furries

A mod is a folder of plain files: a `mod.ff` text file, PNG pictures and WAV
sounds. Nothing in a mod runs as code, so mods are safe to install and every
computer that loads the same mods plays exactly the same game, online too.

What a mod can do:

| Category | What it is |
|---|---|
| **arena** | new levels, drawn as pictures, with the original's springs, fans and moving platforms |
| **weapon** | new weapons (up to four more) or changed original ones: bouncing, homing, exploding, spread shots, fire |
| **rules** | gravity, jump height, lives |
| **skin** | replacement pictures for anything in the game, by image number |
| **sound** | replacement or extra sound effects |

One mod can do several of these at once; the category is what Warpzone files it under.

**Only your own work.** Mods must not contain anything taken from the original
game (pictures, sounds, levels), recoloured or not. A mod may *use* the original
pictures the player imported, by number (see below); it just must not ship them.

Three complete examples live in [`mods/`](../mods): `snowball-arsenal`
(weapons), `midnight-peaks` (an arena) and `low-gravity` (rules).
`mods/make_art.py` draws their pictures.

## Trying a mod

```sh
./play.sh --mod path/to/my-mod            # Linux / Deck
Play-Funny-Furries.exe --mod path\to\my-mod   # Windows
```

`--mod` can be given several times; mods load in that order and later ones win.
In the player menu, X / punch switches between the arenas, and the menu lists
the loaded mods. `--arena N` starts on the N-th mod arena.

## Getting mods from Warpzone

In the Warpzone launcher, the **Mods** tab of Funny Furries installs mods and
keeps one active set. The game loads that set at every start. When you host a
Warpzone room, the room carries your mod set; anyone who joins downloads exactly
those mods first, and plays your arena. Ranked queues match you with players who
have the same set. Every mod version on Warpzone is checked by a moderator first.

To publish your own:

```sh
wz register YourName
wz mod-new my-mod/              # writes my-mod/warpzone-mod.json; set category, licence, game_version ">=0.5.0"
python3 mods/pack.py            # or zip the mod's files, mod.ff at the top of the archive
wz mod-upload funny-furries my-mod/warpzone-mod.json build/mods/my-mod-1.0.0.zip
```

## `mod.ff`

```
FFMOD 1
# comments start with #
image 1024 snowball.png            # a new picture, numbered 1024-1535
image 1026 snow-cannon.png 5 -1    # ... with its hot spot (x y); otherwise its centre
image 52 my-own-body.png           # a number below 1024 replaces that original picture
sound 9 zap.wav                    # a sound slot: 0-7 and 16-23 replace the original's, 8-15 are new
weapon 4 name=SNOWBALLS speed=55 gravity=20 pellets=3 spread=2 bounces=1 shot=1024
rule gravity 28
rule jump 36
rule lives 5
level midnight-peaks.ff            # an arena of this mod
```

File names are relative to the mod folder; `..` and absolute paths are refused.
A mod with any line the game does not understand is left out completely, with
the line number on the console.

The original's sound slots: 0 punch, 1 ice gun, 2 flame thrower, 3 rocket, 4 burn,
5 bonus appears, 6 death, 7 explosion, 16 jump, 17 landing, 18 spring, 19 splash,
20 jetpack, 21 shot hits a wall, 22 pickup, 23 hit.

### Weapons

Slots 1-3 are the original ice gun, flame thrower and rocket launcher; slots 4-7
are new. New slots must be used in order (4 before 5). Every weapon slot is also
a pickup that appears in the arena. A `weapon` line changes only the keys it
names; a new slot starts from a plain gun.

| Key | Meaning | Original ice gun |
|---|---|---|
| `name` | shown in the HUD, letters, digits, `-` | ICE |
| `speed` | in eighths of a pixel per tick (50 ticks per second) | 100 |
| `gravity` | added to the falling speed every tick, 1/256 pixel | 0 (flames: 64) |
| `life` | ticks before the shot ends | 100 |
| `damage` | health taken on a hit | 6 |
| `knock`, `lift` | push away and up on a hit (eighths of a pixel per tick) | 6, -7 |
| `recoil` | pushes the shooter back on every shot (eighths of a pixel per tick) | 4 (rocket: 15) |
| `cooldown` | ticks between shots | 8 |
| `ammo`, `max` | shots a pickup gives, most you can carry | 25, 50 |
| `homing` | turns this many steps per tick toward the nearest opponent | 0 (rocket: 1) |
| `blast` | 1: explodes where it ends | 0 (rocket: 1) |
| `flame` | settles on floors and burns this much per touch instead of hitting | 0 (flames: 4) |
| `bounces` | walls and floors it bounces off before it ends | 0 |
| `pellets`, `spread` | shots per pull of the trigger, fanned out by `spread` of 32 directions | 1, 0 |
| `sound` | sound slot | 1 |
| `shot`, `pickup`, `hand` | picture numbers of the shot, the pickup and the gun in the hand | original art |

### Picture numbers

Numbers 0-1023 are the original game's pictures from the player's own import;
the import directory (`~/.local/share/funny-furries/arena-v8-…`, or
`%LOCALAPPDATA%\funny-furries\…` on Windows) has them as `image-21-<number>.png`
for you to look at. A replacement keeps the original's hot spot unless you give one.

## Arenas

An arena is its own file, listed in `mod.ff` with `level`:

```
FFLEVEL 1
name Midnight Peaks
picture sky.png 0 0              # pictures are drawn in order, back to front
picture terrain.png 0 0
fill 102030 0 0 800 40           # a coloured rectangle
gradient 06102a 1b2552 0 0 800 560   # top colour, bottom colour
collision collision.png          # black = wall, blue (0,0,255) = ledge you can jump up through
solid 0 520 350 40               # or rectangles: x y width height
platform 300 360 200 3
scoreboard                       # the original two-player panel at the bottom
spawn 130 430                    # where furries start and come back: x, y of the feet
bonus 130 405                    # where pickups and bombs appear
place spring-up 16 504           # water, fan-left, fan-right, fan-up, spring-up, spring-down,
place fan-up 384 544             #   spring-left, spring-right: top-left corner, original look
place wind-up 352 300 96 260     # wind-left, wind-right, wind-up: an invisible push area (x y w h)
moving 360 110 230 520 1         # moving ledge: x y, leftmost x, rightmost x, speed
```

The screen is 800 × 600; the arena is the top 800 × 560 and the scoreboard the
bottom 40. A level needs at least two `spawn` points. As in the original, once
an arena has a wind area its fans are only decoration and the wind areas push.
Springs, fans and moving ledges look like the original's (from the player's
import); without an import they are left out. Moving ledges start to the right,
turn at their ends and when two of them meet; only
the first 16 of a level move.
