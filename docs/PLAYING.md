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
the original help file; movement constants and timings are provisional. The
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
