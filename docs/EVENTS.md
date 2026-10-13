# Event structure export v4

This bounded M0 slice exports the **structure** of frame and global event programs in
unprotected CnC projects. It does not decode gameplay opcode or parameter meanings and
cannot yet specify movement, combat, weapon trajectories or event execution.
All opcode/parameter meanings are explicitly `unknown`, including familiar-looking
opcodes. Frame records now carry evidence-based local object-slot candidates;
this aids reading the events without inventing runtime behaviour. Editor group
boundaries and stored titles are annotated separately in v4.

Use the same Python 3.10+, externally supplied pinned KlikBack reader and local
original as the [project index](EXPORTER.md):

```
python3 tools/event_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
python3 tools/event_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src --text
```

Each invocation writes one file: `export/<source-sha256>/events.json`, or
`events.txt` with `--text`. Both contain original event data. Never commit,
publish or release them. The text labels rows, conditions, actions, numeric
opcodes/references, local object-slot candidates and typed raw parameters in storage order; it does not turn
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
  fingerprints. `schema_version` is 4 and `exporter` is `event-dump/4`.
  Version 4 adds row `event_group_annotation`, program `event_groups` and
  `coverage.editor_group_structure` in frame and global programs. All prior
  raw fields and reference annotations are unchanged. Version 3 added `object_reference_annotation` to frame records and two coverage
  flags. Existing raw fields, order, offsets, parameters and global programs
  are unchanged. Version 2 added structured global programs and refused
  unsupported global containers; that validation remains. Consumers must check
  the version. Bare `decode_program`/`decode_rows` remain structural decoders
  with group annotations; only `event_document` has frame object-list context
  for reference annotations.
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
  `parameters`. The signed reference and raw header remain untouched; annotation
  is a separate field described below. The parameter count is the stored byte at record offset 10;
  remaining header fields are retained without interpreting them.
- Parameters retain their unsigned two-byte type, stored size including the
  four-byte size/type prefix, and `payload_hex`. Expressions, strings, asset
  references and positions are still opaque; the separate group annotation
  interprets only the supported title field. Unknown types are preserved,
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
  Editor group structure is a limited exception to otherwise unknown meanings;
  it establishes no runtime activation, selection or ordering rules.

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
the pinned external reader without original data and explicitly skips the original-file
tests across all exporters.

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

## Local frame reference candidates

For a positive object type and an unsigned reference below 0x4000, the
annotation looks up that slot in every object-definition list of the **same
frame**. Each candidate retains the actual frame `block_id`, original object
`id`, name, numeric/type name, global flag and deleted flag. IDs are never
compacted. Global-flagged local headers are still local storage evidence; a
match does not establish which runtime payload backs them. Reference-only
slots can match even when they have no local artwork payload.

`reference_raw_u16` is the unchanged reference word interpreted unsigned.
`status` distinguishes:

- `local_slot_match`: exactly one candidate, live and of the record's type.
- `missing_local_slot`: no candidate in this frame.
- `deleted_local_slot`: exactly one candidate, explicitly deleted.
- `type_mismatch`: exactly one live candidate with a different stored type.
- `ambiguous_local_slot`: more than one candidate; all are retained in block
  order, even if only one has the matching type. No list is selected silently.
- `non_object_type`: zero/negative record type; no object candidates guessed.
- `encoded_reference_unresolved`: positive type with reference word >=0x4000;
  no global/shortcut/qualifier target guessed, including the signed negatives.

Unresolved references are evidence, not malformed input. Global event programs
have no selected frame context and receive no object-reference annotations. This slice does
not resolve global definitions, parameter-embedded references, extension type
IDs to module names, qualifiers, event selection or execution order.
`coverage.frame_local_reference_candidates` is true;
`coverage.global_reference_resolution` remains false. Readable text adds one
REFERENCE line per frame record, with JSON-escaped candidate names so newlines,
quotes and control characters in the original cannot create fake event lines.

Independent mapping evidence is pinned KlikBack
`tgf/block3.py::columns_from_events`, which uses the reference word at record
+4 to index local definitions and handles high-bit/shortcut references separately.
The annotation deliberately stops before those encodings. The local original's
7,573 frame records contain 4,613 exact local matches, 2,958 non-object types
and two unresolved encoded references. Direct event-source-word reads, external
object definitions and editor-column reconstruction verify every candidate.
Synthetic fixtures establish deleted/missing/type-mismatched/ambiguous cases,
separate frame scopes, repeated lists and safely escaped names; these statuses
are not all present in the original. No runtime observation or behaviour proof
is implied by editor/storage evidence.


## Editor group structure (schema 4)

Only a row's first **condition** with signed object type -1 and opcode -10 or
-11 is treated as an editor group open or close. The external pinned reader's
`common/reconstruct_event_test.py::group_marker` establishes the bytes FF F6 /
FF F5 at row+16. Other object types, action records and later conditions with
those same opcode bytes remain ordinary rows. Positive/negative stored row
sizes do not change this rule.

Every row receives `event_group_annotation`: `kind` (open/close/event), outer
`enclosing_open_row_ids` in nesting order, nullable `matching_row_id` and nullable
`title`. Open/close marker rows exclude their own group from the enclosing list;
ordinary rows include every open group. Pairing is by a per-program nesting
stack and storage row IDs, never by an opaque word, title or runtime group ID.
Programs never share a stack. The program's `event_groups` lists `open_row_ids`,
`unclosed_open_row_ids`, `unmatched_close_row_ids` and balanced/unbalanced status.
Unbalanced programs are retained with explicit missing partners; no row is
inserted, deleted or repaired. An enclosing list in an unbalanced program is
only the literal marker stack, not proven runtime membership.

An opening condition with exactly one type-38 parameter of stored size 88
has a supported title: two raw little-endian u16 prefix words, followed by an
80-byte field. `prefix_raw_u16` preserves both words without labelling flags,
identity or initial activation. `field_hex` retains the complete field including
nonzero bytes after NUL; `bytes_hex` stops at its first NUL, or keeps all 80 bytes
if none is present. `byte_view_latin1` is a reversible display of those bytes,
not a claim about the original code page (`source_encoding: unknown`). Unknown
sizes or absent/duplicate type-38 parameters leave title null while preserving
all raw parameters. No unrelated parameter type is decoded. Readable output
adds JSON-escaped GROUP lines and a GROUP_STRUCTURE summary, so source names
with control characters cannot introduce false event rows.

Name offset/80-byte extent have independent evidence in pinned KlikBack
`common/global_event_reconstruct.py::group_records`. That helper is used only
for its row/title traversal, not its newer global-container dialect or prefix
word labels. The implementation is ours; no reader code is bundled. Every local
original title agrees with that helper and separate source-byte reads. All 41
open/close pairs are balanced: 21 frame groups (one in the second frame, two in
each following frame) and 20 global groups. The title field includes named
movement, animation, underwater and weapon sections, but names alone do not
prove those behaviours. Nested/unbalanced groups, ambiguous title parameters,
full-width names, non-ASCII byte views and nonzero NUL tails have synthetic
proof; the original's groups are flat.

This adds a navigation aid for the behaviour specification. It does not infer
activation/deactivation actions, active-at-start flags, global execution order,
physics, controller ownership or gameplay semantics. Raw record/parameter
`meaning` remains unknown. Existing research-v1 bundles contain the prior
component version: move them aside explicitly before a new combined export;
immutable repeat checks deliberately refuse to replace their old bytes.
