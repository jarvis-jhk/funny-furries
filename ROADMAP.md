# Roadmap

## M0 — Exporter
- [x] Deterministic project index: frame/object slots, segment/bank inventory,
      source/reader fingerprints, strict input checks and synthetic/original tests.
- [x] Ordered frame-event structure in JSON/readable text, raw typed parameters,
      explicit unknown meanings, lossless reconstruction and strict validation.
- [x] Local PCM WAV/MIDI export preserving audio bank slots and sample/music bytes,
      strict format checks and atomic immutable bundles; original content ignored.
- [x] Local mode4 TGF image export to RGBA PNG preserving bank slots, colours,
      explicit transparency and raw anchors; strict decoding and immutable bundles.
- [x] Lossless frame-header and placement-slot/record storage JSON, preserving
      gaps, pointer order and unknown fields; arena semantics remain undecoded.
- [x] Active animation/direction storage and ordered image-bank handles, with
      opaque timing/selection fields, original bytes and unresolved references retained.
- [x] Ordinary/quick-backdrop header artwork: image handles, editor fill colors
      and orientation, raw headers; global resolution and arena semantics remain open.
- [x] Score/lives/counter artwork sections and counted image lists, with opaque
      modes/attributes retained; numeric rendering and player ownership remain unknown.
- [x] Ordered global-event programs with preserved opaque header/editor bytes,
      source extents, lossless reconstruction and readable text; semantics stay unknown.
- [x] Frame-event local object-slot candidates with names/types/flags, unresolved
      encodings and ambiguous lists explicit; global/runtime semantics remain open.
- [x] One-command atomic research bundle composing all supported exports, with
      source/reader agreement, version/hash manifest and immutable repeat checks.
- [x] Editor event-group markers, per-program nesting/pairs and stored titles,
      retaining unknown title shapes/unbalanced programs and opaque activation words.
- [x] Ordered expression-token storage and embedded frame-local object candidates,
      preserving opaque prefixes/suffixes and unknown operator/evaluation semantics.
- [x] Position-parameter object references and creation targets with role-specific
      absolute sentinels and frame-local candidates; coordinates/flags stay opaque.
- [x] Event audio-handle candidates joined to application sound/music bank slots,
      with gaps/duplicate banks explicit and all playback semantics still unknown.
- [x] Object-parameter local slot candidates in readable events, with opaque neighbour
      words retained and global/encoded references explicitly unresolved.
- [x] Event-group parameter storage and explicit stored-word title candidates,
      preserving runtime words/partial keys and ambiguous local/global matches.
- [x] Action frame-target words and lossless application level-number word views,
      with explicit table-index probes; CnC runtime destinations remain unresolved.
- [x] Runtime-proven integer expression literal values in readable events, retaining
      raw bits and unsupported shapes; compound evaluation remains unresolved.
- [x] Runtime-proven byte string expression literals with bounded NUL, reversible
      byte views and opaque tails; encoding and compound evaluation remain unknown.
- [x] Runtime-proven numeric addition token annotations, with wrapping integer
      arithmetic documented and nonnumeric/dynamic expression results unresolved.
- [x] Runtime-proven minus-token subtraction/prefix negation annotations, with
      operand order and wrapping numeric arithmetic; actual contexts/results unresolved.
- [x] Runtime-proven numeric multiplication token annotations, preserving wrapping
      32-bit results and unresolved operand contexts/nonnumeric expression semantics.
- [x] Runtime-proven signed division token annotations, with truncation toward zero,
      zero-divisor result and CPU overflow exception; runtime recovery stays unknown.
- [x] Runtime-proven signed remainder capability, including dividend-preserving zero
      divisors and CPU overflow; original project contains no instances.
- [x] Runtime-proven recursive operand and evaluator-stop token annotations,
      retaining unknown delimiter roles/pairing and unevaluated dynamic expressions.
- [x] Runtime-proven closed ungrouped integer expression results, preserving raw-code
      priority, wrapping intermediates and CPU faults; dynamic forms unresolved.
- [x] Runtime-proven closed recursive integer operand results, with both evaluator
      stops, nested prefix signs and ordered faults; dynamic/function forms unresolved.
- [x] Placement first-word/local-object-slot equality probes, preserving actual
      frame/block scopes and ambiguity; runtime references/coordinates stay unproven.
- [x] Runtime-proven event position coordinate inputs, preserving signed/raw X/Y
      words and flags with actual object/global/spawn positions unresolved.
- [x] Runtime-proven placement creation coordinate inputs, preserving signed/raw X/Y
      words and independent override rules; final positions/arena geometry stay open.
- [x] Runtime-proven placement creation type inputs, preserving opaque high bytes
      and all local-header comparisons; allocation/global/arena semantics stay open.
- [x] Runtime-proven frame dimension inputs from both header extents, with signed
      size/clipping arithmetic and unresolved arena collision/window semantics.
- [x] Runtime-proven quick-backdrop dimension inputs from definition headers,
      with signed rectangle arithmetic and ordinary/image/global/collision limits.
- [x] Ordinary-backdrop image-bank dimension candidates, preserving conflicting
      banks and local/global handles; runtime selection/arena geometry remain open.
- [x] Runtime-proven complete backdrop header-to-placement refresh inputs, with
      ordered writes, masked type bits and opaque copied fields; actual selection unresolved.
- [x] Frame-local backdrop placement probes and conditional refreshed record bytes,
      preserving ambiguous/global-flagged candidates and unsupported live selection.
- [x] Runtime-proven conditional quick-backdrop rectangle inputs, with signed
      runtime translation rules and explicit zero-translation previews; live bounds unresolved.
- [x] Runtime-proven conditional quick-backdrop fill dispatch and call inputs,
      preserving mosaic-zero fallback, gradient swap/flags and unresolved clipping/drawing.
- [x] Runtime-proven conditional ordinary-backdrop rectangle consumer inputs, with
      explicit image-bank dimension assumptions and unresolved lookup/live geometry.
- [x] Runtime-proven conditional backdrop metadata-call argument inputs, preserving
      ordinary origin-word overlap and quick zero extension; callee lookup remains open.
- [x] Runtime-proven type23 prefix transport and conditional signed comparison inputs,
      preserving unknown indices/high bits and unevaluated dynamic/event results.
- [x] Runtime-proven immediate scalar parameter getter inputs, with exact type
      dispatch, WORD zero extension and DWORD transport; caller meanings unresolved.
- [x] Runtime-proven parameter address getter inputs, distinguishing header/payload
      transport from scalar values and preserving unresolved caller content semantics.
- [x] Runtime-proven type22 expression getter inputs and conditional closed integer
      returns, with dynamic forms/CPU faults separated and caller semantics unresolved.
- [x] Runtime-proven type16 packed coordinate getter inputs, preserving axis word
      order and discarded helper carry with live object/failure values unresolved.
- [x] Runtime-proven type1 conditional object getter inputs, keeping runtime-gate
      branches, first-word selector storage and editor references separate; live selection unresolved.
- [x] Runtime-proven type42 fixed value/control-word getter inputs, retaining
      opaque intervening bytes and unmasked word wrapping; original instances absent.
- [x] Runtime-proven type45 expression getter inputs and conditional lone byte-string
      address/closed integer returns, with dynamic forms and caller meanings unresolved.
- [x] Runtime-proven remaining header-address parameter getter inputs, preserving
      type48 local/global storage and unproven caller/content semantics.
- [x] Runtime-proven type46 expression getter capability, retaining lossless token
      storage/conditional string and integer returns; original instances absent.
- [x] Runtime-proven random expression transition/scaling and conditional literal
      argument inputs, retaining unknown live state/results and unsupported argument shapes.
- [x] Runtime-proven indexed value-table expression inputs, retaining low-word
      wrapping/conditional slots and unresolved live contents/table meanings.
- [x] Runtime-proven closed integer value-table argument inputs, retaining recursive
      stops, first-token return cursors and CPU faults with live values unresolved.
- [x] Runtime-proven closed integer random argument inputs, retaining recursive
      stops, first-token return cursors and CPU faults with live RNG state unresolved.
- [x] Runtime-proven conditional value-table set/subtract/add action inputs, with
      shared indexed storage, ordered faults and unresolved live event/table values.
- [x] Runtime-proven conditional value-table comparison inputs, with signed
      prefix dispatch, ordered faults and unresolved live table/condition results.
- [x] Runtime-proven fixed carry returns for two system conditions, preserving
      opaque headers/unused parameters and unresolved live condition/row results.
- [x] Runtime-proven conditional group-action row-flag write inputs and signed
      link traversal, preserving stored offsets and unresolved live targets/activation.
- [x] Runtime-proven conditional group-flag condition inputs and header-bit carry
      returns, preserving runtime offsets and unresolved live row/group selection.
- [x] Runtime-proven conditional current-row bit test-and-set capability, preserving
      both carries/conditional writes and unresolved live row/bit lifecycle; original instances absent.
- [x] Exporter from the decompiled project: events as readable text, images/sounds as files,
      arenas as JSON. This doubles as the behaviour spec. Nothing exported is committed.
      Closed 2026-10-14 (Jan: the steps were far too small for a simple game). Images, sounds,
      animations, backdrops and readable events are exported; that is enough to build M1.

**Direction (Jan, 2026-10-14):** no more byte-level reverse engineering for its own sake. No
emulator-proven slices of single evaluator handlers. Remaining semantics (arena geometry,
spawns, movement constants, weapons) are worked out on demand while building the engine:
read the exported events, look at the decompiled project, compare with the running original.
Work in big steps: one session should move a whole milestone item forward, not one detail.

## M1 — One arena 1v1
Done when: one arena plays 1v1 on keyboard + two controllers and feels like the original.
Aim for this in two or three large sessions.
- [x] Native fixed-tick 1v1 prototype: movement, melee/three weapons, pickups,
      lives/respawns/wins, keyboard/two controller seats, local original arena/art/audio.
- [x] SDL2 engine plays one arena 1 vs 1 like the original (same jumps, trajectories, weapons),
      fixed tick, deterministic, keyboard + two controllers; checked against reference
      evidence and two virtual pads. Feel tuning follows Jan's feedback on releases.
- [x] Test release: GitHub prerelease for Linux/Windows/Deck that imports the player's
      own FF2 Xmas copy at first start (no original data in the release).
      Shipped v0.1.0 prerelease on 2026-10-15; physical play feedback remains open.

Human testing never blocks an item (Jan, 2026-10-15): ship a release, keep going,
fix what Jan reports.

## M2 — All arenas, 4 players, Deck
- [ ] All arenas, menus, scoreboard.
- [x] Four players (green/yellow furries, extra spawn points, four-field HUD), modes FFA and 2v2.
- [x] Controller hotplug, "press A to join", Steam Input; Linux/Windows builds, Deck installer,
      fault relay. Shipped v0.2.0 prerelease 2026-10-16; physical 3-4 pad/Deck play is feedback.

## M3 — Rollback online
Done when: a prerelease where 2-4 copies connect by join code over UDP (direct/LAN or STUN hole
punching) and play an FFA/2v2 match with rollback netcode; a lossy, delayed multi-process test stays
in sync.
- [x] Own rollback (no GGPO/GekkoNet needed: the simulation is one plain struct), join code, online
      lobby, STUN + ntfy hole punching, LAN broadcast, desync checksums. Shipped v0.3.0 prerelease
      2026-10-16; play across two real home networks is feedback.
- [x] Warpzone integration (combined roadmap `furries-warpzone-online`): our rollback netplay over
      libwarpzone 0.1.0 (`src/wz.c`, virtual socket in `net.c`); unlisted rooms with six-letter codes,
      direct or relayed, RTT/relay shown; `--warpzone-join`/`--warpzone-host`; name prompt; ranked
      1v1/ffa/2v2 queues, first to three, placements + `ff_game_hash` reported and rated. Own join codes
      stay the fallback. Shipped v0.4.0 prerelease 2026-10-16. Not done (later): public room browser,
      approve/knock rooms, mod sync, leaderboards, update check; descriptor `tier` raise asked of the
      warpzone lane.

## M4 — Mods
- [x] Data-only mods (Jan, 2026-10-16: "add mod support through Warpzone, figure out what makes
      sense"): arenas drawn as PNG pictures with a collision picture and the original devices,
      new/changed weapons as behaviour switches (bounce, homing, blast, flame, pellets), rules
      (gravity, jump, lives), image and sound replacements. Loaded from the Warpzone launcher's
      active set or `--mod`; rooms carry the host's lockfile and guests sync it before connecting;
      ranked queues use it as ruleset. Three example mods in `mods/`. docs/MODDING.md.
- [ ] Report faults through Warpzone (warpzone lane, t_mvc434i38k2u7, Jan's request t_mvc38s7b0g6uv): once
      libwarpzone 0.1.3 is released, pin it, send caught faults with `wz_report(wz,"bug",<stable title>,<detail>)`,
      write title+backtrace to a file in the crash handler and send it on the next start with
      `wz_report_problem(NULL,"funny-furries",<version>,"crash",...)`; game id "funny-furries" routes to this lane.
      Same bump fixes the ranked lobby hang (warpzone t_mvc51iags4f1z): pin CI's warpzone-server/wz to 0.1.3,
      handle PEER_LEFT→PEER_JOINED with a new peer id by re-adding the slot by account, re-run CI ranked tests.
      Blocked: only v0.1.2 is out (checked 2026-10-17). Launcher-started crashes are already reported by Warpzone.
- [ ] Publish the example mods on the public Warpzone (needs the descriptor live, then Jan's approval).
- [ ] Animated mod pictures (sequences with speed) and mod furry skins with all animation frames.

