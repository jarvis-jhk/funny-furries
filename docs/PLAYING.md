# Development prototype

This is the first engine, not a release or a claim of original gameplay fidelity.
The native game runs at 50 fixed ticks per second. Integer simulation, seeded RNG,
input history and a portable state checksum are separate from SDL rendering/audio.

On Debian/Ubuntu, install `cmake pkg-config libsdl2-dev libsdl2-image-dev
libsdl2-mixer-dev`, then:

```
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Debug
cmake --build build/native -j2
ctest --test-dir build/native --output-on-failure
build/native/funny-furries
```

Without local original data it opens an asset-free practice arena. F1 shows the
controls and starts play. Red: F/H move, T jump, Z punch, A weapon, Q jetpack.
Blue: arrows move/jump, Ctrl punch, Shift weapon, slash jetpack. Each controller:
stick/D-pad, A jump, X punch, B/right trigger weapon, Y/left trigger jetpack.
Start dismisses help or pauses. P pauses, R resets the match, Escape exits.
Focus loss pauses and clears keyboard state. Two controller seats are independent;
unplugging one preserves the other and a replacement takes the free seat.

Combat supports fists, ice, flame, rockets, health/fuel pickups, finite ammo,
three lives, invulnerable respawns, match wins and automatic new rounds. Yellow
practice pickups are labelled I/F/R/H/J. Health/damage and ammo quantities follow
the original help file; movement constants and timings still need acceptance.
Frame-3 shooting rows now
supply ice/flame cooldowns of eight ticks and rocket cooldowns of fifty; shot
speeds use their stored 100/57/40 speed settings at the engine's 1/8 scale. The
practice level is ours and is not an original arena.

`--smoke 1000 --screenshot build/frame.bmp` runs a bounded automated input sequence.
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` permits offscreen CI operation. This
checks the actual renderer, asset loading and game loop; it does not prove hardware
controller feel. Tests attach two real SDL virtual controllers and exercise held
input, separate seats, removal, replacement and keyboard focus handling.

Unexpected native faults use an optional `FF_FAULT_REPORT_URL` environment variable
with the private lane report endpoint. A separate courier posts a fixed anonymous
version/device-class/category payload; the process never waits for the network.
No endpoint or identity is compiled into the game. Invalid options/imports are user
errors and are not reported. Delivery is best-effort and needs `curl` on PATH.
The public ntfy/issue bridge and Windows/Deck packaging belong to M2; this prototype
has only been built/run on Linux.

## Play the first original arena locally

First create the research bundle from your own decompiled CnC project, using the
[exporter instructions](PROJECT-BUNDLE.md). Then import that bundle:

```
python3 tools/import_arena.py --bundle export/<source-sha256>/research-v1
build/native/funny-furries --data export/arena-1
```

The importer defaults to storage frame 3 (the original menu's level 1), with
512 scenery layers, multipart red/blue animations, all three weapon/pickup
sprites and eight sound effects. Original PNG/WAV files are copied into an atomic,
immutable local directory. Repeating the command verifies identical contents;
changed output is refused. Supply `--output export/another-name` after changing
the importer. Input files, filenames and hashes are checked before publication.
Every original artifact remains ignored. Nothing is downloaded, bundled in git,
or redistributed. `--frame` can select another 800x600 frame for research; only
frame 3 has been exercised as the M1 arena.

Local global-flagged backdrop headers have stale artwork handles. The importer
uses header word +40 to select the global header and requires its name/type to
match; a mismatch is refused. This fixes the visibly incorrect local-header
scenery observed during development. It is specific to the supported project,
not a general global-object runtime resolver.

Collision masks now combine foreground backdrop obstacles with the original hidden
`up` and active ice surfaces. The stored placement direction selects each marker's
artwork; an overlapping `Changer` selects its short direction-16 variant at start.
These surfaces catch falling players and allow jumps from below. This replaces the
first prototype's blanket solid-snow approximation. Storage frame 3 imports 30 `up`
markers plus active ice surfaces, and retains all 16 usable initial/Start candidates.

Water, fans, directional bouncers and two moving platforms use original local art.
Hidden Wind L/R/up placements supply the fan-force rectangles; only the actual fan
art is drawn. The old approximate reach is retained for asset-free practice data.
Moving platforms travel one pixel per tick between their surrounding `reverse`
markers, including player carry in either direction. Their positions are shared by
rendering and simulation. Swimming, fan forces, bounces and body collision shapes
still need play comparison. Bombs now spawn from original Bonus points using a seeded
trap timer: falling/bouncing, walking and flying variants can be punched or shot,
and explosions trigger chains. Contact and blast each deal eight health, with one
blast hit per player, animated original explosion art and its eighth sound effect.
Hazard movement, lifetimes and explosion collision shapes remain approximations.
Imported bonuses use those same 24 original Bonus points,
with an initial 300..599-tick delay and later 100..999-tick intervals; traps use
400..799 initially, then 200..1099. Practice still begins with immediate pickups.
These ranges follow the readable event constants; RNG/selection order is ours.

The original Windows game was actually opened under Wine and level 1 selected for
visual comparison. Its scenery and the prototype agree after linking globals;
our HUD replaces the lower scoreboard. This observation does not establish equal
jump arcs, movement acceleration, weapon timing, moving-platform paths or physical
controller feel. The follow-up Wine recording measured about 64 pixels of jump
rise; the native
jump now rises 63.25 pixels (44/8 initial velocity, 2/8 gravity), and running caps
at 25/8 pixels/tick. This is a spatial comparison, not a frame-exact timing proof.
Rocket steering, fan/swim/bounce response, collision bodies and physical controller
feel remain M1 acceptance work, so the roadmap item stays started by Sol.

Rockets now turn toward the living opponent in 32 discrete directions and are
turned by hidden wind regions. Their artwork follows the simulated heading.
Global rows 362–369 supply the targeting, wind steering and eight-point direct
hit; frame rows 18/19 supply speed 57 and cooldown 50. The native turn currently
uses one direction step per tick. This is an event-based approximation pending
measured original turn-rate/speed comparison. Vertical and diagonal shots use
pixel substeps, including one-pixel walls, and preserve fractional displacement.
