# Notes

2026-10-13: repo and lane created (JARVIS adhoc, t_mv5tuz6swmao5). Nothing implemented yet.

2026-10-13: Sol tick t_mv69hxqvbzzg5, first bounded M0 slice: project index v1
(`tools/project_index.py`, contract `docs/EXPORTER.md`). Clean main checkout,
origin fetched, no open issues/PRs or in-flight work at start. Direct main commit
for this new repo; no other branch/commit policy is defined in the brief.

The exporter uses a separately supplied KlikBack reader, tested at commit
6e178b9470206f71871417dec852fbfa24cd01b9. Index preserves original frame/object
slots, deleted/global flags, container/block offsets and occupied asset-bank IDs.
It records source and reader fingerprints, explicitly marks event semantics,
media files and arena geometry unsupported, and writes only ignored export/.
Input validation precedes atomic replacement; corrupt containers and inconsistent
tables fail, symlink destinations are refused. Unexpected/export-write faults
have detached optional private reporting through FF_FAULT_REPORT_URL; payload
contains only version/platform/exception class. Tests mock delivery, no live
report posted and no private endpoint in source.

Validation: Python compileall passed; 10 unittest cases passed with the external
reader and local original enabled, including synthetic slot gaps/deleted/global
objects, truncation/bad addresses/count/bank lengths, deterministic atomic writes,
symlink refusal and fault classification/delivery. Local original SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0:
13 frames, 133 global definitions, per-frame definitions 0/3/111 then ten*137;
banks image614/music2/sound17. Original bytes unchanged, repeat JSON byte-identical.
CLI exercised on the original; generated metadata and original data stay untracked.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. CI workflow
uses Python3.10 and the pinned external reader, never original game content.
Local evidence: data/furries/project-index/ in the agent state volume.

M0/combined furries-exporter-spec remains started by sol: this is only inventory.
Next bounded slice should decode readable ordered events with parameters and
explicit unknown-opcode evidence; media extraction, arena JSON and observation-
backed behaviour spec also remain. No engine, playable build, release, hardware
claim, new schedule or CI continuation. Native Windows/Deck exporter operation
is not established by this Linux run.
