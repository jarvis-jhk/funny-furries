# Frame layout structure v2

This M0 research slice exports frame headers and object-placement **storage**
as local JSON. It supplies the lossless placement tables needed for a later
arena decoder. Version 2 adds first-word/local-object-slot equality probes.
It does not yet establish runtime object references, coordinates,
collision geometry, player spawns, drawing order or playable arenas.

Use the Python 3.10+ and externally supplied KlikBack reader from
[EXPORTER.md](EXPORTER.md):

```
python3 tools/frame_layout.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Output is `export/<source-sha256>/frame-layout.json`, ignored by git. It contains
original frame data: never commit, publish or release it. All container and
placement validation completes before a single atomic file replacement.
Repeated runs on identical source/reader bytes are byte-identical. Symlinked
output directories and targets are refused. The original is never modified.
Exit codes and detached private `FF_FAULT_REPORT_URL` fault handling match the
other exporters (0 success, 2 invalid input, 1 unexpected or write fault). No
endpoint, paths, exception text or original data enters fault reports.

## Contract

- Source and external reader fingerprints match the project index.
- `schema_version` is 2 and `exporter` is `frame-layout/2`. Existing raw fields,
  record/slot order, pointer aliases and header bytes are unchanged.
- Every frame retains its zero-based storage ID, absolute segment-header
  offset, and exact pre-block header as `header_hex`. The reader establishes
  header sizes 0xB8 or 0x78; header field meanings remain unknown.
- `placements` lists every block of kind 3 in frame order. `block_id` is its
  index among all frame blocks; `frame_offset` is its block-header offset
  relative to the frame payload. A missing block is distinct from a present
  empty block; repeated blocks remain separate.
- A placement payload begins with a little-endian u16 slot count and that
  many little-endian u32 pointers. `records_offset` is `2 + 4 * count`.
  Pointers are relative to that following record area, **not** the payload
  start. The stored sentinel 0xFFFFFFFF means an unused slot.
- Every slot is retained as its numeric `id`, `pointer_raw_u32` and nullable
  `record_id`. Slots may address records in a different order or share one
  record; aliases are retained without inventing extra instances.
- The supported dialect stores 32-byte records. Each exported record retains
  its storage ID, offset relative to the placement payload, `raw_hex`, and
  `meaning: unknown`. No word is labelled as a resolved object ID or x/y coordinate.
  Within `layout_document`, each record adds `object_slot_probe`, described below.
  The standalone `decode_placements` function remains a context-free storage decoder.
- The record area must be divisible by 32. Every live pointer must be aligned
  and in bounds, and every stored record must be referenced. No trailing or
  unreachable bytes are discarded. Other record dialects are refused.
- Placement payload byte length and SHA-256 permit independent reconstruction.
  `coverage.placement_storage` and `frame_headers` are true; semantics,
  geometry, spawns and behaviour remain false.

## Evidence and limits

The pointer-table shape and unused-slot sentinel have external evidence in
pinned KlikBack `tgf/unprotect.py::repack_placement_block`. That source does
not establish pointer origin or record fields. Pointer origin and the 32-byte
record extent were checked against every placement block of the local FF2 Xmas
decompiled original: after the table, the complete payload consists of exactly
the referenced records, with no gap or tail. This is evidence for this dialect,
not a universal Clickteam format claim.

All 13 frame headers and all 12 placement payloads reconstruct byte-for-byte.
The payloads contain 10,141 slots and 7,968 distinct stored records, with gaps
preserved. The original fixture checks each slot pointer by a separate direct
table read and each referenced record against its original byte span. Synthetic
fixtures independently exercise reversed pointer order, unused slots, aliases,
empty/missing/repeated blocks and both header sizes. Truncated tables, unaligned
and out-of-range pointers, unreferenced storage, malformed late blocks, atomic
write failures, symlinks and safe fault handling are tested.

CI uses the pinned external reader and explicitly skips the original fixture
unless `FF_TEST_PROJECT` is supplied locally. Neither tests nor CI contain game
assets. Decoding record/header fields needs separate evidence, ideally a paired
editor/runtime or controlled original observation. Arena classification,
geometry/spawns JSON and the behaviour specification remain open.

## First-word local slot probes

For each stored record, `object_slot_probe` retains `record_offset: 0` and
`word_raw_u16`: the unsigned little-endian word at record bytes 0..1. It looks
up that number as a slot in every object-definition list of the **same frame**.
Candidates retain the actual definition `block_id` among all frame blocks,
`id`, `name`, `type`, `type_name`, `flags`, `global` and `deleted`. Definition
order and multiple lists remain visible. A global-flagged local header is a
candidate; application-global definitions and other frames are never searched.

`status` is `missing_local_slot` for no equality candidate, `local_slot_probe`
for exactly one live candidate, `deleted_local_slot` for exactly one deleted
candidate, or `ambiguous_local_slot` for multiple candidates, even if only one
is live. There is no proven expected type, so no type is inferred from another
record word. All u16 values, including 0x4000, 0x8000 and 0xFFFF, receive the
same equality lookup: event reference encodings and placement **pointer**
sentinels do not establish record-word semantics.

Every annotation states `runtime_resolution: false` and
`evidence: stored_word_local_slot_equality`. These are explicit index probes,
not a proven CnC record-field specification. An independently traversed original
has exactly one live same-frame slot for every one of its 7,968 records,
including backdrop, active, display and extension definitions. That complete
correlation supports investigation of the first word as an object reference;
it does not prove runtime identity, global body selection, creation, collision,
draw order or that every placement is an initial live instance/player spawn.
No editor/runtime instructions were executed for this claim.

`coverage.placement_object_slot_probes` is true; `placement_semantics`,
`arena_geometry`, `spawns` and `behaviour` remain false. Raw record/header bytes
and complete placement reconstruction remain lossless. Pointer aliases keep
one stored record and one probe, rather than multiplying presumed instances.
The research bundle automatically includes schema 2 and its component version;
an existing different immutable bundle must be moved aside before regenerating.

Synthetic tests cover differing frame scopes, actual block identities, missing,
deleted and repeated/ambiguous definitions, unsigned boundaries, no global
fallback, aliases, gaps, reversed pointers, empty/repeated placement blocks and
JSON-escaped names. A late unaligned placement refuses both standalone JSON and
combined bundle before writing or fault reporting. The original-file test reads
each word directly from its source span and builds candidates independently
with the pinned reader's `object_definitions`, without calling the annotation
or project-index helpers. Every source span and all twelve placement blocks
still reconstruct, and repeat documents/input bytes remain identical.
