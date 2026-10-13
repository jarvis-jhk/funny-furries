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
