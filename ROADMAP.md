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
- [ ] Exporter from the decompiled project: events as readable text, images/sounds as files,
      arenas as JSON. This doubles as the behaviour spec. Nothing exported is committed.

## M1 — One arena 1v1
- [ ] SDL2 engine plays one arena 1 vs 1 like the original (same jumps, trajectories, weapons),
      fixed tick, deterministic, keyboard + two controllers.

## M2 — All arenas, 4 players, Deck
- [ ] All arenas, menus, scoreboard.
- [ ] Four players (green/yellow furries, extra spawn points, four-field HUD), modes FFA and 2v2.
- [ ] Controller hotplug, "press A to join", Steam Input; Linux/Windows builds, Deck installer,
      fault relay.

## M3 — Rollback online
- [ ] Rollback netcode (GGPO/GekkoNet), lobby with join code, NAT traversal, VPS relay fallback.
