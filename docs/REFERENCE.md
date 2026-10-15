# M1 reference checks

The reference is the user's local, unmodified Funny Furries 2 Xmas executable
and its exported frame/global events. Original images, recordings, project data
and the executable stay outside git. These observations do not claim identical
CnC scheduling, RNG or physical controller acceptance.

The running original was opened under Wine and storage frame 3 selected. Its
scenery identified the stale local backdrop handles. Earlier jump recordings
show about 64 pixels of rise; our fixed-tick jump reaches 63.25. Run speed is
25/8 pixels/tick. This is spatial agreement, not a frame timing certification.

The next comparisons use the original's readable event rows directly:

- Frame 8–15: fists cost 12 health, with horizontal 22/upward 12 impulses
  and a 25-tick hand cooldown. Held punch repeats after that cooldown.
- Frame 16–20/30: ice/flame use cooldown 8, rockets 50; shot speeds 100/57/40.
- Frame 22–25: ice costs 6 health, with horizontal 6/upward 7 impulses.
  There is no freeze/control lock in these rows.
- Global 362–369: rockets seek the opposing living player, turn with parameter
  1 and are redirected by wind; contact costs 8 before the separate explosion.
- Global 373–382: explosions cost 8 once per player and push 50 away on both axes.
- Frame 40–43/global 385–396: fire remains on surfaces, causes four-point hits
  with a six-tick victim gate, and changes to its ending animation at age 250.
- Global 175–190/219–234: swimming uses held upward force 2 against downward
  force 1, horizontal target speed 18 and vertical threshold 20.
- Global 296–311: horizontal/downward springs set speed 100; an upward spring
  reverses falling speed plus 20; wind adds a directional force of 5.

Those speed/impulse settings use the same 1/8 scale as the measured jump/run.
The native rocket turns one of 32 direction steps per tick. Original extension
scheduling/turn rate, fire fall/fade motion and exact contact timing remain
approximations. Respawn timing and trap motion are provisional too; blast contact uses the
current frame bounds rather than exact transparent-pixel overlap.

A second actual Wine session collected an eight-round launcher and fired it into
nearby terrain. Private timestamped screenshots show ammo consumption, the
projectile and the resulting explosion. The short, obstructed shots corroborate
operation but cannot measure a long homing trajectory. Do not present them as
turn-rate acceptance.

The original's collision sensor alpha masks give these extents relative to the
feet origin (the original artwork origin plus 16): head 14×12 at (-7,-26), lower
body 14×16 at (-7,-16), wall 22×13 at (-11,-21), feet 18×9 at (-9,-8). The native
solid silhouette combines the first three; one-way support uses the 18-pixel
foot span, including a one-pixel ledge. Wind/spring contact uses the corresponding
foot/head/side sensor rectangles. This is a compact collision model, not the
original's ordered overlap-correction engine.

Local automated checks cover deterministic replay, simultaneous damage/round
completion, original arena loading, collision edges, homing/vertical shots,
fire gates and controller hotplug. Two SDL virtual controllers also drive an
actual complete mutual-KO match and automatic new round through the input layer,
then move and jump independently. The keyboard is exercised through SDL key
messages. Virtual devices establish wiring; physical two-pad feel requires a
human acceptance pass on the target hardware.

Further running-reference checks used the moving platform as a one-pixel/tick
clock. Its pixels match the local source artwork. The old jump recording spans
about 44 ticks from departure to landing, versus 45 in the native test, with
roughly 63–64 pixels of colored-body rise versus 63.25 native feet rise. Animation
pixels and capture ordering introduce about a pixel/tick of uncertainty. A new
continuous-Up recording shows repeated jumps without releasing the key; native
jump now repeats on landing too. The capture host runs the original at a variable
rate (about 44 platform pixels/second here); do not retune the 50 Hz simulation to
that host's wall clock.

Platform reversal is a leading-edge overlap, not center-to-marker travel. The
upper platform was observed turning near left-edge X=688. Its 48-pixel hidden
collision image and the two-pixel-wide reverse markers give X=352..688; the lower
platform's markers similarly give 176..272. The importer derives these from the
opaque sensor bounds. This fixes the previous half-platform-width overshoot.

Weapon muzzle offsets now come from each facing hand image's action point minus
its hotspot (and the feet-origin shift). Rocket muzzles are ±23/-11; ice and
flame differ. Imported explosion bounds grow from 20×20 to 64×64 with the rendered
frames. A returning rocket can hit its shooter for both contact and blast damage.
Old local imports keep prototype muzzle/blast defaults; a fresh v5 import is
needed for the revised geometry and platform paths.
