# Event structure export v1

This bounded M0 slice exports the **structure** of frame event programs in
unprotected CnC projects. It does not decode opcode or parameter meanings and
cannot yet specify movement, combat, weapon trajectories or event execution.
All meanings are explicitly `unknown`, including familiar-looking opcodes.

Use the same Python 3.10+, externally supplied pinned KlikBack reader and local
original as the [project index](EXPORTER.md):

```
python3 tools/event_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
python3 tools/event_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src --text
```

Each invocation writes one file: `export/<source-sha256>/events.json`, or
`events.txt` with `--text`. Both contain original event data. Never commit,
publish or release them. The text labels rows, conditions, actions, numeric
opcodes/references and typed raw parameters in storage order; it does not turn
unknown codes into guessed English behaviours. The JSON supports subsequent
semantic decoders without reparsing the original bytes.

The index's container, object-table and bank validation runs first, then every
event block is validated before output starts. Writes replace one file
atomically; separate JSON/text invocations are not a transactional pair. Failed
validation leaves outputs unchanged. Symlink output directories and targets
are refused. Identical input/reader bytes produce identical outputs without
timestamps or local paths. Exit codes and detached optional private reporting
via `FF_FAULT_REPORT_URL` match the index: input errors 2, actual faults 1,
success 0. Fault payloads carry only exporter version/platform and exception
class; no path, event data or exception text leaves the process.

## JSON contract

- `source` and `reader_sha256` retain the project's and reader module's exact
  fingerprints. `schema_version` is 1 and `exporter` is `event-dump/1`.
- `frames` preserve every zero-based frame slot. A missing event block is an
  empty `programs` list, distinct from a present program with no rows.
- Each program's `block_id` is its position among **all** frame blocks,
  `frame_offset` is the block header's offset relative to the frame payload,
  and `bytes` is the event block payload length. Multiple event blocks remain
  separate and ordered.
- The supported event header is `Fra\0`, little-endian version `0x0217`.
  `program_offset` is 10 relative to the event block payload, after the six-byte
  signature/version and four-byte program length. Headerless runtime programs
  and other versions are refused pending separate evidence.
- Rows have a 14-byte preserved `header_hex`, signed stored size, condition and
  action counts, and ordered `records`. The condition records precede actions.
  Both positive and negative signed row lengths are retained. The program must
  end with exactly one zero size word, with no trailing bytes.
- Records preserve a 14-byte condition header or 12-byte action header, signed
  one-byte object type/opcode, signed two-byte raw object reference, and ordered
  `parameters`. No local/global/qualifier/system interpretation of references
  is imposed. The parameter count is the stored byte at record offset 10;
  remaining header fields are retained without interpreting them.
- Parameters retain their unsigned two-byte type, stored size including the
  four-byte size/type prefix, and `payload_hex`. Expressions, strings, asset
  references and positions are still opaque. Unknown types are preserved,
  never discarded. Declared counts must consume each record and row exactly.
- Row, record and parameter `offset` values are relative to the **program**;
  `bytes` always includes the corresponding header. Their IDs are zero-based
  storage positions, not runtime identities.
- `auxiliary` preserves the following length-prefixed block 2 and remaining
  block 3 bytes with offsets relative to the event block payload. Editor
  layout/comment data is opaque. The decompiler may have regenerated editor
  metadata; retaining it does not recover lost authored comments.
- Top-level `global_events` retains each global-event segment as an opaque
  payload, with its segment-list position (`segment_id`), absolute segment
  header offset, length, fingerprint and `raw_hex`. Its container differs from
  the frame `Fra` header; no frame or global-event merge is invented.
- `coverage.frame_event_structure` is true; `opcode_semantics`,
  `parameter_semantics` and `global_event_structure` remain false.

## Evidence and remaining work

The row/record layout is grounded in the pinned external reader's
`tgf/format.py` and `tgf/block3.py` traversal. Parameter boundaries are also
validated by full byte reconstruction against every frame event block of the
local decompiled FF2 Xmas project. This establishes storage structure, not
execution semantics. Tests contain only independently authored synthetic data.

The original-file test runs only when `FF_TEST_PROJECT` is supplied locally.
It verifies frame row counts `0/4/52` then ten times `113` (1,186 total), 2,490
conditions, 5,083 actions and 6,685 parameters; reconstructs every complete
frame event block and the opaque global payload byte-for-byte; and checks
unchanged input and repeat output. Synthetic tests cover ordering, unknown
codes, signed references, empty/absent programs, bad sizes/counts/terminators,
truncation, atomic output failures, symlinks and fault classification. CI uses
the pinned external reader without original data and explicitly skips both
original-file tests (index and events).

Next slices: decode the global-event container; map opcode/parameter semantics
with independent evidence; export media and arena geometry; build a behaviour
spec from these exports and actual original observations. M0 remains open.
