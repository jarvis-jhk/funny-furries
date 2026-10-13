# Event structure export v2

This bounded M0 slice exports the **structure** of frame and global event programs in
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
  fingerprints. `schema_version` is 2 and `exporter` is `event-dump/2`.
  Version 2 retains all frame fields and the global raw payload fields from v1,
  adds structured global programs, and refuses unsupported global containers
  instead of silently exporting them as opaque. Consumers must check the version.
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
- Top-level `global_events` retains each global-event segment in segment order,
  with segment-list position (`segment_id`), absolute segment header offset,
  complete payload length, SHA-256 and `raw_hex`. Multiple global segments stay
  separate; missing segments differ from a present program containing no rows.
  No frame/global-event merge or execution order is inferred.
- Supported global payloads have a **40-byte header without a Fra signature**.
  Four little-endian u32 fields are interpreted: total payload length at +0,
  header extent at +8 (must be 40), program offset at +12 and program byte length
  at +16. The declared total must match the segment payload, program offset
  must be at least 40, and program offset plus length must equal the total.
  At least the two-byte row terminator must be present. Other header words
  remain opaque; no guessed editor-field relationships are imposed.
- Each global segment adds `header_hex`, `program_offset`, `program_bytes`,
  `rows` and `auxiliary`. Row/record/parameter structure and offsets follow the
  same contract as frame programs, with offsets relative to the global program.
  The single auxiliary entry (ID 0) preserves all bytes between header end and
  program start, with payload-relative offset 40, length and unknown meaning.
  It is not split or interpreted as editor metadata. An empty region remains
  a present zero-byte entry. Header + auxiliary bytes + reconstructed rows and
  terminator reproduce the entire global payload, independently of `raw_hex`.
- `coverage.frame_event_structure` and `global_event_structure` are true;
  `opcode_semantics` and `parameter_semantics` remain false. Global record
  object references remain signed raw numbers, without runtime resolution.

## Evidence and remaining work

The row/record layout is grounded in the pinned external reader's
`tgf/format.py` and `tgf/block3.py` traversal. Parameter boundaries are also
validated by full byte reconstruction against every frame event block of the
local decompiled FF2 Xmas project. This establishes storage structure, not
execution semantics. Tests contain only independently authored synthetic data.

The original-file test runs only when `FF_TEST_PROJECT` is supplied locally.
It verifies frame row counts `0/4/52` then ten times `113` (1,186 total), 2,490
conditions, 5,083 actions and 6,685 parameters; reconstructs every complete
frame event block byte-for-byte; and checks
unchanged input and repeat output. Synthetic tests cover ordering, unknown
codes, signed references, empty/absent programs, bad sizes/counts/terminators,
truncation, atomic output failures, symlinks and fault classification. CI uses
the pinned external reader without original data and explicitly skips the nine
original-file tests across all exporters.

Global header-field interpretation is observation-backed against the single
63,602-byte original global segment, not an independent universal format spec.
Its header extent is 40, program starts at 9,916, and 53,686 program bytes run
exactly to payload end. All 398 rows, 765 conditions, 968 actions and 1,475
parameters reconstruct byte-for-byte; the pinned reader's independent
`event_groups` traversal agrees on every row offset and length. The 9,876-byte
intervening region stays opaque, including any data regenerated by decompiling.
This does not prove which global events run in which frames, their order relative
to frame events, or any opcode meaning. The original has no font-bank segment
or type-3/4 text/question data blocks; none were invented for this slice.

Synthetic global tests cover known ordered rows/parameters, arbitrary opaque
header words and editor bytes, no editor bytes, empty programs, missing/repeated
segments, overflow-sized and malformed extents, unsupported header lengths,
truncated records/parameters/terminators and late-invalid segments before either
JSON/text write. Existing frame, atomic write/symlink and detached private fault
handling tests still run. Unknown global dialects now fail validation with exit 2.

Next slices: map opcode/parameter semantics with independent evidence; resolve
object/global references and extension data; export arena geometry; build a
behaviour spec from these exports and actual original observations. M0 remains open.
