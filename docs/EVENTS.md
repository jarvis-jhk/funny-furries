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
  fingerprints. `schema_version` is 7 and `exporter` is `event-dump/7`.
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
not resolve global definitions, non-expression parameter references, extension type
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

## Expression token storage (schema 5)

Parameters of types 15, 22, 23, 45, 52 and 53 now add `expression_storage`.
All existing raw fields, row/group/reference annotations and ordering remain;
parameter and token `meaning` stays unknown. No arithmetic, literal, function,
comparison, selection or runtime evaluation semantics are inferred. Other
parameter types remain opaque. The six-type set and token traversal have
independent evidence in pinned KlikBack
`common/reconstruct_event_test.py::EXPRESSION_PARAMETER_TYPES` and
`common/event_object_registry.py::expression_object_slots`. This is our own
implementation, checked against the original editor parameters; importing an
external compiled-format helper does not establish every editor dialect.

The payload (excluding its four-byte size/type header) starts with an opaque
little-endian u16 `prefix_raw_u16`. Tokens begin at payload offset 2. Each
nonzero token has a u16 `code_raw_u16`, u16 byte length, and unchanged `raw_hex`.
The exported ordered tokens retain zero-based storage `id`, `payload_offset`,
`bytes` and nullable `object_reference_annotation`. The first zero code is a
two-byte terminator, recorded at `terminator_payload_offset`; `suffix_hex`
preserves every subsequent byte without interpreting it, including nonzero
synthetic tails. Prefix + raw tokens + zero terminator + suffix reconstructs
exactly the original parameter payload. Empty expressions are distinct from
absent parameters. Offsets are relative to this parameter's payload, unlike
the existing parameter offset relative to the event program.

For a token whose code's low byte is in 1..127, the external reference helper
establishes a u16 object word at token+4 and a minimum eight-byte token. The
remaining token words stay opaque. `expected_type` is that low byte only for
codes >=0x3000; lower codes have no established expected object type and use
null. Each such token keeps its unsigned reference word. A frame expression
uses the same frame's local object lists and preserves every candidate and
block identity. Matching a unique live slot without an expected type yields
`local_slot_candidate`, rather than claiming a type match. With an expected
type, the existing match/mismatch rules apply. Missing, deleted, ambiguous or
encoded (>=0x4000) references remain explicit and unresolved. No list is chosen
silently, including when one of several candidates has the expected type.
Global expressions and standalone program decoding have no selected frame;
their object tokens keep `frame_context_unresolved` and empty candidates.
Non-object tokens have a null annotation, without assigning a guessed name.

Recognized expression parameters must contain a complete prefix, token headers,
in-bounds lengths of at least four bytes, complete object-token headers when
applicable, and a terminator. Violations now refuse the whole JSON/text/bundle
with exit 2 before writing or reporting, rather than treating those payloads
as undifferentiated bytes. Unknown token codes with valid storage remain raw.
Schema 4 consumers must accept the new annotations/version, and previous
immutable research bundles need explicit move-aside before regenerating.
The earlier synthetic two-byte type-22 placeholder was updated to include an
empty expression terminator; its previous shape is now a malformed-input case.

Readable text adds one JSON-escaped EXPRESSION line per recognized parameter,
so original names/control characters cannot create false event lines.
`coverage.expression_token_storage` is true; `parameter_semantics`,
`opcode_semantics` and global reference resolution remain false.

All 3,868 original expressions (2,461 type22, 1,400 type23, seven type45) contain
4,485 tokens across 22 distinct codes. All source byte spans, parameter
reconstruction and embedded reference words match independent reads and the
external helper. The 288 embedded object words include 98 frame-local
candidates (17 expected-type matches, 81 without expected types) and 190
unresolved global references. Every local candidate's ID/name/type/flags/block
identity agrees with external object definitions in its actual frame. Suffixes
are empty for 3,686 expressions, eight zero bytes for 173 and four zeros for
nine. Types15/52/53 and malformed, empty, unknown-code, repeated-list,
type-mismatch, encoded-reference and nonzero-tail shapes have synthetic proof,
not original/runtime observation. Geometry, spawns and behaviour remain open.


## Position-parameter object references (schema 6)

Types 9, 16, 18 and 21 now add `position_reference_storage.references` to the
parameter. Minimum total parameter lengths (including the four-byte size/type
header) are respectively 34, 26, 36 and 34 bytes. Shorter supported shapes are
refused before JSON, text or bundle output; longer payloads retain every byte.
All previous fields, raw payloads, expression/group annotations and ordering
are unchanged. Unknown parameter types remain opaque.

Each of the four types carries a u16 reference at payload offset 0 (parameter
+4). Types 9 and 18 also carry a u16 creation-target reference at payload offset
24 (parameter +0x1C). The offset is relative to the payload, independent of the
condition/action header and of the frame/global container. Every entry retains
its `role`, `payload_offset`, `reference_raw_u16`, `status` and `candidates`.

The position-reference values 0xFFFE and 0xFFFF are explicit
`absolute_position_sentinel` entries with no candidates. This distinction
applies only to the position reference: the same words in creation targets
remain unresolved. The sentinel alone does not establish coordinates or
which absolute-position mode the runtime uses.

Other frame references use the existing frame-local slot candidate resolver:
unique live slots yield `local_slot_candidate`, without inventing an expected
object type. Missing, deleted, ambiguous and encoded references retain their
existing explicit statuses. Actual object-list block IDs, slot IDs, names,
types and global/deleted flags remain in candidates. Local global-flagged
headers are storage candidates, not resolved global definitions. Global
programs retain `frame_context_unresolved` (or the absolute sentinel); no frame
is assigned to them. Creation targets and position references are resolved
independently, and the containing record's type is never used as their type.

Readable text adds one JSON-escaped POSITION_REFERENCES line per recognized
parameter, preserving names with control characters. The research bundle
includes the same annotations and updates its component version and hashes;
immutable older bundles must be explicitly moved aside before regeneration.
`coverage.position_reference_storage` is true, while parameter evaluation,
global resolution, arena geometry and behaviour remain unsupported.

Evidence: pinned KlikBack 6e178b9470206f71871417dec852fbfa24cd01b9,
`common/event_object_registry.py::event_object_slots` and
`common/reconstruct_event_test.py::remap_object_position_parameter` agree on
these four minimum sizes, both word locations and the role-specific sentinel
handling. Synthetic tests independently observe the remapper changing exactly
those reference words. Original-file tests compare every position/creation
reference with direct source reads and the separate event-object traversal,
and compare local candidates with the external object definitions. All 1,263
original position parameters (1,150 type 9, three type 16, 110 type 18) and
2,523 reference words are retained; type 21 is synthetic-only evidence.

The remaining parameter bytes, including coordinates, flags, cached words,
shoot speed, relative-position selection and extension tails, remain opaque.
These annotations do not establish action/opcode meanings, runtime execution,
spawn positions or a complete behaviour specification.

## Audio bank reference candidates (v7)

`event-dump/7`, schema7 adds `audio_reference_storage` to parameter types6
(sample/sound) and7 (music). Pinned KlikBack6e178b9
`common/reconstruct_event_test.py::compiled_event_to_editor_event` identifies
the little-endian u16 handle at parameter+4 (payload+0): its conversion clears
exactly this word to0 for samples and0xFFFF for music. It retains the name and
other bytes. The exporter reads the word without rewriting anything. A
parameter must contain at least those two payload bytes; all remaining bytes
stay opaque in the existing `payload_hex`. Other parameter types are unchanged.

The annotation contains `kind`, `payload_offset`, `reference_raw_u16`, `status`
and `candidates`. A standalone program decoder has no application banks and
uses `bank_context_unresolved`. In a complete project, both frame and global
programs use the same application-level banks, partitioned by sound/music.
Only occupied slots with the exact stored ID are candidates. Status is
`bank_slot_candidate` for one, `missing_bank_slot` for none and
`ambiguous_bank_slot` for multiple matches in repeated banks. Missing/empty
banks, slot gaps and duplicate banks are preserved; no candidate is chosen
from an ambiguous result. Handles0/0xFFFF have no invented sentinel rule.

Each candidate carries `segment_id`, slot `id`, `kind`, bank-relative record
`offset`, record `bytes` and `record_sha256`. These identities join directly to
`audio-manifest.json` in the research bundle (or the standalone audio manifest),
whose entry supplies the exported filename. The event exporter never invents a
filename for an unsupported audio dialect or requires audio decoding to expose
a raw bank candidate. It never matches by name or guesses ownership from the
containing event record. `AUDIO_REFERENCE` lines provide the same JSON annotation
in readable text. `coverage.audio_bank_reference_candidates` is true; opcode,
parameter evaluation and playback semantics remain unclaimed.

Independent direct slot-table/parameter-word reads verify all891 original
references (870 sample/21 music) against the audio manifest. All have one exact
kind/slot candidate. The original's16-byte parameter name-prefix spans also
match the corresponding bank headers, independently corroborating these slot
identities; no production name-field decoder or encoding claim is added.
Synthetic fixtures test both parameter types/record roles, frame/global scope,
opaque tails, minimum lengths, gaps, absent/empty/repeated banks, the valid slot0,
0xFFFF without a sentinel assumption, and media identity in a complete bundle.
The pinned converter test verifies its exact two-byte change separately.

Migration from schema6: only the audio annotations, coverage flag and version
are added. Existing raw fields, object/group/expression/position annotations
and lossless reconstruction stay unchanged. Existing immutable research bundles
will refuse changed event bytes; preserve/move the old bundle aside explicitly
before generating the new one. Audio/media bytes and standalone audio schema
remain unchanged. This is storage-to-bank evidence, not proof of which opcode
plays/stops/loops audio or its timing, volume, name resolution or runtime use.
