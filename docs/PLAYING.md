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

Without local original data it plays an asset-free practice arena. The game opens
in the player menu: up to four seats, each joined with its own jump button (A on a
controller) and left again with its weapon button (B). Jetpack (Y) switches between
free for all and 2 vs 2; Start or Enter begins once two players (four for 2 vs 2)
are ready. Seat 1 is blue, 2 red, 3 green, 4 yellow; in 2 vs 2 blue+green play
red+yellow, and teammates' fists and shots do not hurt each other (explosions do).
Green and yellow reuse the player's own blue and red furry art with the body hue
turned at load time; nothing recoloured is shipped.

Seats 1 and 2 also have keyboards. Blue: arrows move/jump, Ctrl punch, Shift weapon,
slash jetpack. Red: F/H move, T jump, Z punch, A weapon, Q jetpack. Every controller:
stick/D-pad, A jump, X punch, B/right trigger weapon, Y/left trigger jetpack.
Controllers take seats 1-4 in connection order, so pads 3 and 4 play green and
yellow. Start pauses, Back or Escape returns to the menu, P pauses, R resets the
match, F1 shows controls, Escape in the menu exits. Focus loss pauses and clears
keyboard state. Unplugging a pad keeps the other seats and a newly connected pad
takes the free seat. A furry that loses its three lives stays out until the round
ends; the last furry (or team) standing scores a win.

On the Steam Deck the built-in controls are the first pad; extra pads join as
seats 2-4. Steam Input's default gamepad layout matches the mapping above.

Combat supports fists, ice, flame, rockets, health/fuel pickups, finite ammo,
three lives, invulnerable respawns, match wins and automatic new rounds. Yellow
practice pickups are labelled I/F/R/H/J. Health/damage and ammo quantities follow
the original help file; movement constants and timings still need acceptance.
Frame-3 shooting rows now
supply ice/flame cooldowns of eight ticks and rocket cooldowns of fifty; shot
speeds use their stored 100/57/40 speed settings at the engine's 1/8 scale. The
practice level is ours and is not an original arena.

`--smoke 1000 --screenshot build/frame.bmp` runs a bounded automated input sequence
(`--players 2-4`, `--teams` for 2 vs 2, `--lobby` to render the player menu).
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` permits offscreen CI operation. This
checks the actual renderer, asset loading and game loop; it does not prove hardware
controller feel. Tests attach four real SDL virtual controllers and exercise held
input, separate seats, removal, replacement, a four-pad 2 vs 2 match and keyboard
focus handling.

Online goes through [Warpzone](https://github.com/jarvis-jhk/warpzone), the
shared online layer of JARVIS's games (`src/wz.c`, libwarpzone 0.1.0 pinned by
SHA-256 in CMakeLists; `-DFF_WARPZONE=OFF` builds without it). H (or a pad's
Back) in the player menu opens an unlisted room and shows its six-letter room
code; J takes that code; R (or a pad's RB) opens the ranked queues 1 vs 1,
free-for-all of four and 2 vs 2 (one player per device, first to three round
wins). The first Warpzone action asks once for a name, shared with every
Warpzone game on the machine. Warpzone finds a direct path or relays the
traffic, encrypted; the game shows each peer's round trip and "relayed".
Our netplay runs unchanged on top: `ff_udp_virtual` hands its datagrams to
`wz_send` and takes `wz_poll`'s peer data back. Ranked hosts seat the
matchmaker's teams (2 vs 2 = even/odd seats); a match ends at the first fully
confirmed frame where someone has three wins, so every machine reports the same
placements and the same `ff_game_hash` to `wz_report_match`, and the server
rates it. `--warpzone-host`, `--warpzone-join ROOM` (what the Warpzone launcher
and website pass), `--warpzone-code CODE` and `--ranked 1v1|ffa|2v2` do the same
from the command line; `WARPZONE_SERVER`/`WARPZONE_HOME` pick another server or
identity, `FF_WZ_NAME` registers a name without asking, `FF_RANKED_WINS` (tests
only, everyone must agree) shortens a ranked match, `FF_WZ_VERBOSE=1` logs the
library's events. `tests/engine/test_warpzone.py` runs real game processes
against the released warpzone-server: room 2 vs 2 with two players per machine
on a bad line, once direct and once with `relay_only.c` (LD_PRELOAD) dropping
every direct datagram so the relay must carry it, then all three ranked queues
until the server reports "rated".

Without the Warpzone server (offline, or `FF_NET_LAN_ONLY=1`), H falls back to
our own join codes and J accepts them: `--host` / `--join CODE` with
`--local 1-3` do the same from the command line.
The engine side is `src/rollback.c` (snapshots of every frame, prediction
"still holding what they held", re-simulation when a real input differs, an
input delay of two frames, at most twelve frames of guessing, and a checksum of
every 32nd confirmed frame exchanged to detect desyncs) and `src/netplay.c`
(UDP star around the host, which forwards every input to every guest; time
sync by waiting a tick when running ahead). `src/net.c` holds sockets, STUN
(Google/Cloudflare public servers) and the join code: the host's public
address and a 16-bit token in 13 base-32 letters with a check bit. Hole
punching uses the public ntfy.sh over plain HTTP: the guest posts its STUN
address to a topic derived from the code and the host sends to it. Guests
also broadcast on the LAN. `FF_NET_LOSS`/`FF_NET_DELAY`/`FF_NET_JITTER`
(percent, ms, ms) simulate a bad line; `FF_NET_LAN_ONLY=1` skips STUN and
ntfy. Tests: `test_rollback` (in-memory network, 2-4 machines, loss/latency,
against an offline run), `test_net` (codes, STUN parsing) and `test_netplay.py`
(real processes over loopback UDP with simulated loss). `net_probe internet`
checks STUN and the ntfy round trip live; it is not run in CI.

Unexpected native faults use an optional `FF_FAULT_REPORT_URL` environment variable
with the private lane report endpoint. A separate courier posts a fixed anonymous
version/device-class/category payload; the process never waits for the network.
No endpoint or identity is compiled into the game. Invalid options/imports are user
errors and are not reported. Delivery is best-effort and needs `curl` on PATH.
Packaged launches use the anonymous public ntfy/issue relay described in
[RELEASE.md](RELEASE.md); the private environment option above is for local development only.

## Play the first original arena locally

First create the research bundle from your own decompiled CnC project, using the
[exporter instructions](PROJECT-BUNDLE.md). Then import that bundle:

```
python3 tools/import_arena.py --bundle export/<source-sha256>/research-v1
build/native/funny-furries --data export/arena-1
```

The importer defaults to storage frame 3 (the original menu's level 1), with
512 scenery layers, multipart red/blue animations, all three weapon/pickup
sprites and sixteen sound effects; the original's other levels (frames 4-12) go
beside it as `level-<frame>.ff`. The start menu's X/punch cycles through them
(level 1, levels 2-10, then mod levels); `--level N` starts on level N. Original PNG/WAV files are copied into an atomic,
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
Moving platforms travel one pixel per tick and turn when their leading edge
meets a surrounding `reverse` marker, including player carry in either direction. Their positions are shared by
rendering and simulation. Swimming uses continuous held thrust, springs respond only to approach from
their active side, and collision follows the original sensor silhouettes.
These changes still need physical play comparison. Bombs now spawn from original Bonus points using a seeded
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
The event-based weapon/device and collision comparisons are recorded in
[REFERENCE.md](REFERENCE.md). Original extension timing and physical controller
feel remain M1 acceptance work.

Rockets now turn toward the living opponent in 32 discrete directions and are
turned by hidden wind regions. Their artwork follows the simulated heading.
Global rows 362–369 supply the targeting, wind steering and eight-point direct
hit; frame rows 18/19 supply speed 57 and cooldown 50. The native turn currently
uses one direction step per tick. This is an event-based approximation pending
measured original turn-rate/speed comparison. Vertical and diagonal shots use
pixel substeps, including one-pixel walls, and preserve fractional displacement.

The flamethrower leaves falling fire that stops on terrain and burns for about
250 ticks, then fades. Contact costs four health every six ticks, shared across
all overlapping flames. Settled fire can also burn its owner. Ice deals six
health and pushes back/up; it does not disable the victim's controls. Fists add
22/8 horizontal and 12/8 upward velocity; ice adds 6/8 and 7/8; explosions push
50/8 away on both axes. External impulses decay instead of being immediately
clamped to running speed. These changes follow frame rows 12–25/40–43 and global
rows 373–396. Fire shape, fall motion and fade duration are approximations; its
original 250 counter and six-tick damage gate are retained.

New imports include the original looping and ending flame animation frames.
Existing local imports continue to work with their single flame image; reimport
into a new output directory for animated fire. SDL virtual-controller checks
now play a full simultaneous-KO match and its automatic next round through the
actual game input layer, then exercise separate movement and jumping.

Hold jump to jump again on landing; hold punch to repeat at the original 25-tick
hand cooldown. The running original confirms repeated held jumping. Importer v5
also places each weapon at its original hand action point and grows explosion
contact bounds with the artwork. Reimport into a fresh directory to get these
muzzle offsets, blast bounds and corrected platform reversal limits.

## Testing on two physical pads

M1 is ready for release testing. Physical controllers and the Deck are open
checks for Jan on the prerelease, not a gate on publishing it. Confirm the
blue/arrows/first-pad and red/F-H/second-pad seats stay independent while moving,
holding jump, punching and firing. Finish a match, let the next round start,
and unplug/replace one pad without stealing the other seat.

Compare jumps, springs, swimming, platforms, ice, lingering fire and homing
rockets with the original. Report the action, location and affected player.
Approximate timings and collision order will be tuned from this feedback.

## First-start launcher

`tools/launcher.py` imports the player's full-version `funnyfurries.zip`,
`FF2xmas.cca`, or the folder beside `FF2xmas.exe`. It reads the CCA locally,
restores the protected container using the pinned KlikBack reader, and imports
arena 1 without altering the source. The launcher keeps a checked, atomic local
import under the user's application data directory. A damaged cache reopens
file selection. `--reimport` selects another original; `--practice` skips import.
`--fullscreen` fills the display for Deck use.
Started from the Warpzone launcher, `WARPZONE_DATA_FF2XMAS` names the copy it
found on the machine: without a valid import the launcher imports that copy
without asking (also when Warpzone passes `--import-copy`), and a copy it cannot
use only prints why and opens the normal file selection.

Development CLI (requires Python and the separate reader):

```
python3 tools/launcher.py --reader-source /path/to/KlikBack/src --import-copy /path/to/funnyfurries.zip --import-only
```

The release launcher bundles its own Python/reader. Only fixed anonymous
version/OS/fault-category reports go to the public ntfy topic. A detached helper
handles delivery; input errors and missing/unsupported original copies are not
fault reports. Set `FF_NO_REPORT=1` to disable it.
