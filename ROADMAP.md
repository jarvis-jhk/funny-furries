# Roadmap

## M0 — Exporter
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
