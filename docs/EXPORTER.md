# Project index v1

The first M0 slice inventories an unprotected CnC project. A separate
[event structure exporter](EVENTS.md) now preserves ordered frame records and
raw parameters in JSON/readable text. These are research tools, not yet the
asset/arena exporter or a decoded behaviour specification.
The [audio exporter](AUDIO.md) adds original PCM WAV/MIDI files in an ignored,
immutable bundle. The [image exporter](IMAGES.md) adds mode4 RGBA PNG files
with bank IDs, explicit opacity and raw anchors. The [frame layout exporter](FRAME-LAYOUT.md)
preserves frame headers and placement slots/records; arena semantics remain unimplemented.
The [active animation exporter](ANIMATIONS.md) adds numeric animation/direction
slots and ordered image handles; runtime playback/selection remain unknown.

Requirements: Python 3.10+, a separate local checkout of GPL-3.0-or-later
KlikBack, and the player's local original/decompiled project. No third-party
code or original game data is bundled here. The reader tested for this slice is
KlikBack commit `6e178b9470206f71871417dec852fbfa24cd01b9`, module
`src/klikback/core/tgf/format.py`. This tool imports that reader rather than
copying its implementation. Updating the reader requires re-running the tests.

```
python3 tools/project_index.py orig/game.cca --klikback-src /path/to/KlikBack/src
python3 -m compileall -q tools tests
python3 -m unittest discover -s tests -v
```

For parser tests, set `FF_KLIKBACK_SRC` to that source directory. Additionally
set `FF_TEST_PROJECT` to the local decompiled FF2 Xmas project to verify the
original inventory. Without the reader, the index's four parser tests and the
event exporter's two container tests explicitly skip;
portable output/fault tests still run. The audio exporter's two container tests
also require the reader, as do the image exporter's two container tests.
The frame layout exporter's two synthetic container tests also require the reader.
The active animation exporter's two container tests also require the reader.
CI fetches the pinned external reader, runs the synthetic parser tests and
skips only the six original-file tests.

Output is always `export/<source-sha256>/project-index.json`, ignored by git.
Never commit, publish or release it. The JSON contains object names and layout
metadata originating in the user's copy. Input paths, project title and author
are excluded. Original bytes are read once and never modified. The whole index
is validated before an atomic replacement; input errors leave any previous
index intact. Symlinked output directories/targets are refused.

Schema v1 fields:

- `source`: SHA-256, byte length, signature and numeric format version.
- `reader_sha256`: exact reader module content fingerprint.
- `segments`: ordered segment IDs, names, absolute file offsets and payload sizes.
- `frames`: zero-based storage IDs, segment offsets, sizes and block inventory;
  block offsets are relative to the frame payload. `object_lists` retain each
  object-definition block, including empty lists and deleted slots.
- `global_object_lists`: each global-definition list in storage order.
- Objects: original slot ID, name, numeric/type name, flags, global/deleted
  booleans; object offset is relative to its definition-list payload, and nested
  block offsets use the same origin. IDs are never compacted.
- `banks`: image/font/music/sound kinds and occupied slot IDs with offsets/sizes
  relative to the bank payload. Missing slots remain gaps; an absent bank stays
  absent, not an invented empty bank.
- `coverage`: explicit booleans for inventory, event semantics, asset files and
  arena geometry. Only inventory is implemented. A frame is not necessarily a
  playable arena; no coordinates, movement rules or event opcode meanings are
  inferred from this index.

Malformed containers, inconsistent level addresses/counts, protected projects,
TGF projects, incomplete object lists and out-of-bounds bank entries fail with
exit 2. Unexpected implementation failures exit 1. Success exits 0 and prints
only the relative output path. JSON is deterministic for identical input and
reader bytes; there are no timestamps or machine-specific paths.

Set `FF_FAULT_REPORT_URL` locally to JARVIS's private report endpoint to deliver
unexpected implementation faults in a detached process with a two-second network
timeout. It posts lane `furries`, version/platform and exception class only.
Ordinary input errors are not reported; failed output writes are real faults.
No endpoint or secret is stored in the
repo; tests use mocks and never send a real report. Game runtime fault delivery
via ntfy remains part of M2.

Remaining M0 work: decoded opcode/parameter meanings and global events;
remaining object artwork and global reference mapping (active animation image
sequences, mode4 PNG and PCM/MIDI audio now supported);
arena geometry/spawns JSON; a behaviour spec backed by those exports and actual
original observations. These need their own bounded slices.
