# Event structure export v27

This bounded M0 slice exports the **structure** of frame and global event programs in
unprotected CnC projects. It does not decode gameplay opcode or parameter meanings and
cannot yet specify movement, combat, weapon trajectories or event execution.
Raw opcode/parameter `meaning` fields remain `unknown`, including familiar-looking
opcodes. Schema12 separately decodes runtime-proven integer and string literal tokens. Frame records now carry evidence-based local object-slot candidates;
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
  fingerprints. `schema_version` is 27 and `exporter` is `event-dump/27`.
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
parameter and token `meaning` stays unknown. Schema5 inferred no arithmetic, literal,
function, comparison, selection or runtime evaluation semantics; schema11 adds
only independently proven integer literal values as described below. Other
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

In schema6 the remaining parameter bytes stayed opaque. Schema21 separately
exposes coordinate input words and raw flags as described below; cached words,
shoot speed, relative-position selection and extension tails remain opaque.
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


## Object-parameter reference candidates (v8)

`event-dump/8`, schema8 adds `object_parameter_reference` to parameter type1
in both conditions and actions, frame and global programs. Pinned KlikBack
6e178b9470206f71871417dec852fbfa24cd01b9 independently identifies this type
and the little-endian u16 at parameter+6 (`payload_offset: 2`) in
`common/event_object_registry.py::event_object_slots`; its
`reconstruct_event_test.py::compiled_event_to_editor_event` remaps that exact
word for both roles. The supported parameter needs at least ten bytes including
its four-byte size/type header. Shorter shapes fail exit2 before JSON, text or
research-bundle writes or fault reporting. Extra bytes survive unchanged.

The word is an untyped local object-slot candidate, using the existing same-frame
object lists and status vocabulary. No expected type is inferred from the
neighbouring words: the independent registry returns `None` for the expected
type. Unique live slots are `local_slot_candidate`; deleted/missing/ambiguous
lists stay explicit. Words >=0x4000 are `encoded_reference_unresolved` (including
0xFFFE/0xFFFF, with no borrowed absolute-position sentinel). Global programs
retain `frame_context_unresolved` and no candidates; no local list is chosen
for them. Global flags on local definitions are preserved without resolving
application definitions. Candidate names are JSON-escaped on a separate
`OBJECT_PARAMETER_REFERENCE` text line.

All974 original type1 parameters were verified against independent registry
traversal and direct source words:760 frame-local candidates and214 unresolved
global words. This identifies stored relationships for subsequent behaviour
research, without claiming collision/selection/opcode, evaluation, qualifier or
runtime semantics. The entire raw payload, earlier annotations and original
record reconstruction are preserved. Schema/version and the added fields/lines
are the only event-output changes; the composed bundle picks them up normally.
Existing fault handling, atomic writes, immutable repeat checks and private
original-content policy are unchanged.

## Event-group parameter storage and stored-word candidates (v9)

`event-dump/9`, schema9 adds `group_parameter_storage` to type39 parameters
in either conditions or actions. The first four payload bytes are preserved
as little-endian `runtime_raw_u32`. Pinned KlikBack's
`compiled_event_to_editor_event` clears exactly those bytes in **actions**;
executed synthetic and original probes establish that operation. It does not
clear the condition word. The value is never treated as a source row offset,
never dereferenced and never used to select a group.

A complete next u16 at payload+4 becomes `key_raw_u16`; all bytes thereafter
remain `suffix_hex`. Four/five-byte payloads have no complete key and retain
the partial byte in the suffix. Shorter payloads are refused before output.
No key, including zero/0xFFFF, is assigned sentinel semantics.

The new annotation offers **byte-equality candidates**, not resolved activation
or group identity: the key word is compared to the second raw prefix word of
each known-shape type38 title on a group-opening row. That field's meaning was
previously opaque and remains so. Matching candidates include scope, actual
frame/block or application-global segment ID, row ID/offset, matching close
row ID (possibly null), raw title bytes and the Latin-1 byte view. Only the
current frame program and all application-global programs are compared for a
frame parameter. A global parameter compares application-global programs.
Sibling frame programs and other frames are never merged into its scope.

Every matching candidate is retained, including duplicate words/titles,
unclosed groups and simultaneous local/global matches. Status is
`no_key_word`, `no_stored_word_match`, `stored_word_candidate` or
`ambiguous_stored_word`. Unknown title shapes are not fabricated into matches.
The chosen set of candidate scopes is a research search space, not evidence
of runtime precedence, global execution or address resolution. In particular,
a unique match must not be used by an engine as an authoritative target.

Readable `GROUP_PARAMETER` lines JSON-escape names. Existing raw fields,
group pairing and other reference annotations are unchanged. The research
bundle uses the same annotations; its media and all other component bytes
are unchanged. `coverage.group_parameter_stored_word_candidates` is true;
`parameter_semantics`, opcode/global execution and behaviour remain false.

All159 original type39 parameters (115 actions/44 conditions) have a unique
stored-word match in this research search space. Independent direct source
reads and pinned-reader group markers/title spans verify every key/candidate
and lossless parameter byte span. Seventy-one actual original rows also run
through the external converter. This corroborates the storage and equality
relation in this one original, not activation/deactivation/condition polarity,
runtime addresses, a universal CnC layout or a behaviour specification.


## Frame-target storage and level-number index probes (v10)

`event-dump/10`, schema10 adds `frame_target_storage` to **action** parameters
of type26. Pinned KlikBack6e178b9 `compiled_event_to_editor_event` uses a u16
at parameter+4 (payload+0) as a frame-target map key and rewrites exactly that
word. Synthetic and actual original-row probes run this converter separately.
Condition type26 parameters remain unannotated: that converter offers no
condition-target evidence. Recognized actions need at least two payload bytes;
shorter forms refuse exit2 before any JSON/text/bundle write or fault reporting.
Unknown parameter types and all suffix bytes remain unchanged in `payload_hex`.

The annotation preserves `target_raw_u16`, `payload_offset: 0`, and
`runtime_resolution: unknown`. Standalone decoders use `table_context_unresolved`.
The complete project also exports each application segment7, named
`level-numbers` by the CnC reader, as `level_number_storage`. Each retains the
actual segment index/header offset, byte length/hash, complete `raw_hex`, and
ordered little-endian u16 **views** (`id`, `payload_offset`, `raw_u16`). A final
odd byte remains `suffix_hex`. Missing, empty, repeated and odd-length segments
stay distinct. These are storage views, with no inferred header/count/terminator
or table validity rule. The full payload reconstructs exactly from words/suffix.

For research comparison, the raw action target is used as an **index probe**
into each table's complete word views. `probe_method` explicitly names
`raw_target_as_level_number_table_index`. Each candidate carries `segment_id`,
`slot_id`, `payload_offset` and `raw_u16`; zero candidates gives
`table_slot_unavailable`, one `table_slot_probe`, multiple
`ambiguous_table_slot_probes`. Both frame and global programs use the same
application tables. No candidate is selected from repeated tables. Neither
0xFFFF targets nor 0xFFFF table words acquire sentinel semantics. No `frame_id`,
name, destination offset or successful transition is inferred from the probe.

Why the limit matters: the pinned reader's full `frame_item_target_map` reads
MMF chunk0x222B and does not establish the CnC segment7 layout. Applying that
later-format resolver here would invent cross-format evidence. The local original
has one28-byte segment containing14 words, including0xFFFF and a nonidentity
permutation. Its only two type26 actions occur in globals (object type-3/opcode2),
and both contain target13. The explicit index probe reads slot13's raw word1;
that observation does **not** prove a jump to exported frame1 or a one-based
frame13. Runtime destinations, activation/opcode and condition/evaluation
semantics still need separate original/editor/runtime evidence.

Readable `FRAME_TARGET` lines preserve the parameter annotation;
`LEVEL_NUMBER_STORAGE` lines expose the full raw table on one escaped line.
`coverage.frame_target_storage` and `level_number_word_probes` are true;
`frame_target_resolution`, `opcode_semantics`, `parameter_semantics` and the
behaviour specification remain false. Prior raw fields and every earlier
annotation/text line remain unchanged apart from version and these additions.
Only events JSON/text and the composed bundle manifest change; media and the
other research components remain identical. Existing immutable research bundles
must be explicitly preserved/moved aside before regeneration. The optional
private fault handler and atomic/symlink protections stay unchanged.


## Integer expression literals (schema11)

Expression token code0x00FF with extent8 now carries `integer_literal`:
`token_offset: 4`, `value_signed_i32`, `value_raw_u32` and
`evidence: cnc_runtime_dispatch`. The four bytes at token+4 are a little-endian
32-bit integer. Signed and unsigned views retain the same bits. Existing token
raw bytes/offsets/order and reference annotations remain unchanged; the generic
legacy `meaning: unknown` field is retained for consumers. This specific
annotation establishes a numeric literal value, not the meaning of its containing
parameter or event. It applies in both roles, frame/global programs and all six
supported expression parameter types. Readable EXPRESSION JSON includes values.

Only this exact code/extent is supported. Short or extended0x00FF tokens fail
as input errors before any JSON/text/bundle write or private fault report.
Other codes remain opaque; in particular0xFFFF is **not** an integer literal
alias. Prefix words, first terminator, suffix bytes, unary markers, operators,
object tokens and expression evaluation retain their existing treatment.
Two literals separated by a token never become an evaluated expression.
`coverage.expression_integer_literals` is true; `expression_evaluation`,
`opcode_semantics` and `parameter_semantics` remain false. The text's opening
coverage sentence now names this limited decoding instead of calling every
expression value unknown. Immutable bundle migration rules still apply.

Evidence comes from the player's original FF2xmas.exe, SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.
At preferred image base0x400000, entry0x42a417 starts tokens at parameter+6.
Dispatcher0x42a474 sign-extends the token's low/high bytes to object type and
opcode, respectively. Low byte-1 selects pointer slot0x41a384, yielding table
0x41b2b8; opcode0 selects handler0x428823. That handler loads the dword at
token+4 into EAX and clears DX's low16 bits, the numeric result tag. The
caller advances by the u16 extent at token+2. These addresses identify the
examined binary, not offsets exported as game data or runtime dependencies.

Private independent Unicorn2.1.4 execution loads the original PE sections,
executes the actual dispatcher and the lone-literal evaluator0x42a42e, and
checks EAX, numeric tag, token cursor and balanced stack. All3776 original
literal tokens and seven signed boundary inputs pass through each entry
(7566 executions). The original's TEXT_1 section is marked DATA in PE section
flags; `objdump -d` omits it, so the audit uses `objdump -D -j TEXT_1`.
This is isolated instruction execution, not running the game or certifying
movement/combat, compound evaluation, Windows/Deck operation or hardware.

The newer Clickteam runtime offers corroboration only: its EXP_LONG uses a
32-bit signed value but has a wider token code0x0000FFFF. See the
[Clickteam SDK runtime distribution](https://github.com/AITYunivers/CTFJavaSDK)
(revision5f8f266d507a35557e294c62fc8ff418e9335b65, RuntimeSDK.jar,
Expressions.CExp/EXP_LONG). Its different token header is
never used to decode this CnC dialect. No SDK code or original executable bytes
are copied into the implementation, tests or repository. Runtime files,
disassembly, generated JSON/text/assets and the optional emulator stay private
in agent state. CI requires only the pinned KlikBack reader; local original
fixtures separately read literal values directly from source program spans.


## Byte string expression literals (schema12)

Exactly token code `0x03FF` adds `string_literal`. The original CnC runtime
returns a pointer to token+4 and sets DX to1, its string result tag. The
exporter records `token_offset: 4`, `bytes_hex` up to the first NUL,
`terminator_token_offset`, and `suffix_hex` for every byte after that NUL
within this token. `byte_view_latin1` is a reversible byte view, with
`source_encoding: "unknown"`; it does not claim a codepage or Unicode meaning.
Empty strings, odd token extents, high bytes and opaque post-NUL tails stay
lossless. Readable EXPRESSION JSON escapes names, newlines and quotes onto one
line. String tokens in the expression's opaque suffix are not interpreted.

An absent NUL **inside the token** fails with exit2 before JSON/text/research
bundle writes or fault reporting. This intentionally refuses an unbounded
runtime pointer; it never borrows a following token/parameter's terminator.
Other token codes remain opaque, including0x01FF/0xFFFF. Integer literals,
object candidates, all raw fields and original ordering remain unchanged.
`coverage.expression_string_literals` is true, but `expression_evaluation`,
`parameter_semantics`, `opcode_semantics`, and global resolution remain false.
No compound result, filename action, INI access or gameplay meaning is inferred.
Immutable bundles must be moved aside before regenerating changed event bytes.

### Original runtime evidence

Player-supplied FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
dispatcher0x42a474 sign-extends low byte-1 and high byte3, selecting table
0x41b2b8 at slot0x41a384 and its fourth handler0x42881b. That handler returns
`EDI+4` in EAX and sets DX to1; dispatcher then advances EDI by stored token
size. Lone-literal evaluator0x42a42e preserves that pointer and tag. Inspect
`objdump -D -j TEXT_1` because this executable marks runtime instructions as
PE DATA. No executable bytes or original content are committed.

Private independent Unicorn2.1.4 execution in agent state
`data/furries/expression-strings/runtime_oracle.py` loads the player's original
PE sections and runs both entries. All seven original tokens and seven synthetic
cases (empty, path, high bytes, escaped characters, maximal u16 extent and a
post-NUL tail) pass28 runs: returned pointer, byte string+NUL, DX string tag,
next-token cursor and balanced stack. Original tokens all contain the same
14-byte field (13 bytes before NUL), without a tail; that observation does not
establish the string's containing event behavior. Synthetic suffix shapes are
preserved as storage, not claimed as editor-generated layouts. No executable
file API or whole game is invoked by this isolated instruction proof.

Seven new tests cover exact-code isolation, mixed tokens, malformed strings
that cannot borrow a later NUL, both roles/all expression parameter types and
program scopes, readable escaping, lossless reconstruction, immutable repeats,
and late-invalid CLI refusal before all writes/reporting. Original-file test
independently walks the pinned reader tokens and reads values/tails directly
from source-program spans. Native Windows/Deck gameplay remains untested.


## Numeric addition operator token (schema13)

Exactly four-byte token `0x0200` adds `integer_operation` to JSON and the
existing readable EXPRESSION line. `name: add`, `bits: 32` and
`overflow: wrap_modulo_2_32` describe the original evaluator's numeric path.
`required_operand_tag: 0` limits that claim to numeric operands;
`other_operand_tags: unknown` leaves the separate nonnumeric path unresolved.
`evidence: cnc_runtime_operator_table` records the independent runtime proof.
This annotation identifies the token's numeric operation, without determining
the actual surrounding operand types, evaluating dynamic object/file calls,
folding constants or producing an expression result. Strings adjacent to the
operator retain their byte-literal annotations; their concatenation is not
claimed. Schema14 also documents the minus token below; remaining operators and
precedence remain undecoded.

Only the exact supported code/extent is accepted. Short or extended addition
tokens fail as input errors before JSON/text/research-bundle output or private
fault reporting. Token raw bytes, ordering, prefix/suffix and every existing
annotation remain unchanged; the legacy `meaning: unknown` field remains for
consumers. `coverage.expression_integer_addition` is true, while
`expression_evaluation`, `parameter_semantics` and `opcode_semantics` remain
false. Immutable bundles containing earlier event bytes must be moved aside
before regeneration, as with earlier event-schema additions.

### Original instruction evidence and limits

Player-supplied FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
evaluator0x42a42e reads the operation code, advances four bytes, evaluates the
right operand, and selects the function pointer at0x41b574+(code>>8)*2.
For0x0200, the pointer at0x41b578 is0x42a4b5. With numeric tag DL=0, that
handler executes 32-bit EAX+ECX and returns without changing the numeric tag.
Carry/overflow is not converted to a wider result or an exception. DL!=0
branches into a different path which this slice does not implement or certify.
These binary-specific addresses are evidence, never game-data offsets or
exporter dependencies. Inspect `objdump -D -j TEXT_1`; this PE marks the
runtime section DATA. No original instructions or assets are committed.

Private independent Unicorn2.1.4 execution in agent state
`data/furries/expression-addition/runtime_oracle.py` runs both that handler and
the complete evaluator entry against49 signed-boundary pairs and512 seeded
random numeric pairs. All1122 executions verify modulo2^32 results, numeric
result tag and balanced stack; evaluator runs also verify the next-token
cursor. Each of116 original four-byte addition tokens is separately inserted
between independent numeric literal probe operands and executed through the
actual evaluator, bringing the total to1238 runs. This validates the stored
operation code/extent, **not** the results of the surrounding original dynamic
expressions. The original contains no standalone literal+literal expressions.
No functions are mocked as original behavior; the string branch and complete
gameplay are not run by this proof.

Seven new cases cover exact-code isolation, opaque strings/unknown operand
contexts, short/extended operator refusal, all expression types/roles/scopes,
readable escaping, late-invalid refusal before output/reporting, lossless
programs and immutable repeat bundles. The local-original fixture independently
walks pinned KlikBack tokens and reads every operator code/extent directly
from source-program spans. CI runs synthetic cases and explicitly skips the
original fixture unless locally supplied; native Windows/Deck gameplay remains
outside this research slice.

## Numeric minus token (schema14)

Exactly four-byte token `0x0400` has two independently proven numeric uses:
`integer_operation` identifies `subtract`, with `operand_order: left_minus_right`;
`integer_prefix_operation` identifies `negate` at operand entry. Both specify
32 bits, `overflow: wrap_modulo_2_32`, `required_operand_tag: 0` and
`other_operand_tags: unknown`. The binary evidence is
`cnc_runtime_operator_table`; the prefix evidence is `cnc_runtime_dispatch`.
Both annotations are present on every supported token, without selecting its
actual execution context or evaluating any expression. An isolated sign, two
adjacent signs, strings and unknown operands are preserved as token storage;
these annotations do not certify their validity or their runtime results.
In particular, `INT32_MIN` negates to the same bit pattern in the proven numeric
path. String/pointer behavior remains unsupported.

Unsupported short/extended minus tokens fail exit2 before JSON/text/bundle
output or fault reporting. This follows the fixed four-byte consumption in the
original operator and prefix paths. Unknown codes keep their existing storage
rules. Every prior raw field, addition/literal/reference/group annotation and
prefix/suffix remains unchanged. `coverage.expression_integer_minus` is true;
`expression_evaluation`, `parameter_semantics` and `opcode_semantics` stay false.
The existing readable EXPRESSION JSON includes both annotations. Earlier
immutable research bundles must be moved aside before regenerating; media and
other research components do not change.

### Original instruction evidence and limits

Original FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
evaluator0x42a42e selects pointer0x41b57c in table0x41b574 for0x0400.
Handler0x42a529 swaps EAX (right operand) and ECX (left operand), then subtracts
ECX from EAX, giving left-minus-right modulo2^32. Operand dispatcher0x42a474
recognizes0x0400 at entry, consumes four bytes and negates EAX at0x42a4a9 after
loading the operand. This is one prefix sign; arbitrary chains of unary signs
and nonnumeric tags are not certified. The runtime's prefix stack adjustment
uses16-bit SP, so the isolated oracle uses a stack away from a64KiB boundary.
These executable-specific addresses are evidence, not exporter dependencies.
No original instruction bytes, assets or exported metadata are committed.

Independent Unicorn2.1.4 proof is saved privately in agent state
`data/furries/expression-minus/runtime_oracle.py`. The actual binary handler
and complete evaluator each run49 signed-boundary pairs and512 seeded random
pairs. The actual dispatcher and evaluator each execute unary negation for
seven boundaries and512 seeded values. Two additional evaluator streams per
pair exercise `left - -right` and `-left - right`. All63 original minus tokens
are independently inserted between numeric probe literals and passed through
the evaluator. All3345 executions check wrapping results, numeric tags and
balanced stacks; evaluator/dispatcher cases check token cursors. A deliberately
reversed subtraction expectation fails on an asymmetric executed pair.
This proves the two operation paths, not the surrounding original dynamic
expressions, gameplay or native Windows/Deck acceptance; no dynamic functions
are mocked as evidence.

Eight new tests cover exact codes, opaque contexts and both annotations,
unsupported extents, six expression parameter types/both roles/program scopes,
readable output, lossless source reconstruction, late-invalid refusal before
all outputs/reporting and immutable bundle repeats. The optional original-file
fixture reads all63 operator words/extents directly from source-program spans
and independently traverses pinned KlikBack tokens. CI skips that fixture when
the player's local project is absent.


## Numeric multiplication token (schema15)

Exactly four-byte token `0x0600` now has `integer_operation` identifying
`multiply`, `bits: 32`, `overflow: wrap_modulo_2_32`,
`required_operand_tag: 0`, `other_operand_tags: unknown` and
`evidence: cnc_runtime_operator_table`. This describes the independently
executed numeric operation, without inferring the containing operands, choosing
expression contexts, folding constants or evaluating original expressions.
Signed overflow keeps the low 32 product bits, including INT32_MIN times -1.
String/pointer inputs and grammar/precedence remain uncertified. There is no
prefix-operation annotation for this code.

Short/extended recognized multiplication tokens fail exit2 before JSON/text/
bundle writes or fault reporting. Unknown codes retain their storage rules;
all prior raw fields, annotations, prefixes/suffixes and ordering are preserved.
`coverage.expression_integer_multiplication` is true; `expression_evaluation`,
`parameter_semantics` and `opcode_semantics` remain false. The existing readable
EXPRESSION JSON displays the annotation. Earlier immutable research bundles
must be moved aside before regeneration; media and other components do not change.

### Original instruction evidence and limits

Original FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
evaluator0x42a42e selects table0x41b574+(code>>8)*2, so0x0600 selects
pointer0x41b580 to handler0x42a52d. The handler clears EDX, performs signed
32-bit IMUL ECX with EAX and clears DX before returning. EAX is the low 32
product bits; only the low16-bit numeric result tag is certified (the upper
EDX bits can retain part of the product). These executable-specific addresses
are evidence, not exporter dependencies. No original instructions/assets or
exported metadata are committed.

Private independent Unicorn2.1.4 oracle in agent state
`data/furries/expression-multiplication/runtime_oracle.py` executes both the
actual handler and complete evaluator for49 signed-boundary pairs and512
seeded random pairs. Each run checks modulo2^32 result, low16-bit numeric tag
and balanced stack; evaluator runs additionally check the next-token cursor.
The single original multiplication token is separately placed between numeric
probe literals and executed through the evaluator. All1123 runs pass. This
validates operation code/extent, not the original surrounding dynamic
expression, nonnumeric inputs, gameplay or Windows/Deck hardware acceptance.
No dynamic functions are mocked as original behavior.

Eight new tests cover code isolation, opaque/invalid contexts, boundary literals
and mixed existing operations without folding, short/extended refusal, all six
expression types/both roles/scopes, readable annotations, lossless reconstruction,
late-invalid refusal before all outputs/reporting and immutable bundle repeats.
The optional original fixture independently walks source-program token boundaries
with the pinned reader registry and checks the one operator's stored code,
extent and annotation. CI skips that fixture when the player's project is absent.

## Numeric division token (schema16)

Exactly four-byte token `0x0800` now has `integer_operation` identifying
`divide`, `operand_order: left_divided_by_right`, `bits: 32`, `signed: true`,
`rounding: toward_zero`, `zero_divisor_result: 0`, `overflow: x86_divide_error`,
`exception_recovery: unknown`, `required_operand_tag: 0`,
`other_operand_tags: unknown` and `evidence: cnc_runtime_operator_table`.
This describes the independently executed numeric path. It does not identify
actual operand contexts, validate grammar/precedence or fold/evaluate expressions.
For example, -7 / 3 and 7 / -3 return -2, any numeric left operand / 0 returns 0,
and INT32_MIN / -1 triggers the x86 divide-error exception instead of wrapping.
The original process's response to that exception remains unverified; no crash,
recovery or replacement result is claimed. String/pointer inputs remain unknown.
There is no prefix-operation annotation for division.

Short/extended recognized division tokens fail exit2 before JSON/text/bundle
writes or fault reporting. Unknown codes keep their storage rules. All prior raw
fields, annotations, prefixes/suffixes and ordering are preserved.
`coverage.expression_integer_division` is true; `expression_evaluation`,
`parameter_semantics` and `opcode_semantics` remain false. The existing readable
EXPRESSION JSON displays this annotation. Move earlier immutable research bundles
aside before regenerating; media and other research components do not change.

### Original instruction evidence and limits

Original FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
evaluator0x42a42e selects table0x41b574+(code>>8)*2, so0x0800 selects
pointer0x41b584 to handler0x42a535. That handler swaps EAX (right) with ECX
(left), tests the divisor in ECX and returns EAX=0/DX=0 if zero. Otherwise it
sign-extends EAX using CDQ, executes signed IDIV ECX at0x42a53b and clears DX
before returning the quotient. INT32_MIN / -1 traps at IDIV before the tag clear
and return. These addresses are binary-specific evidence, not exporter
requirements. No original instructions, assets or exported metadata are committed.

Independent Unicorn2.1.4 execution is saved privately in agent state
`data/furries/expression-division/runtime_oracle.py`. The actual handler and
complete evaluator each execute49 signed-boundary pairs, four explicit rounding
pairs and512 seeded random pairs. Each of15 original operator tokens is then
inserted between independent numeric probes for both signed rounding directions,
a zero divisor and the overflow pair. All1190 executions pass:1173 return
with checked result, low16 numeric tag and balanced stack (evaluator also checks
cursor), and17 raise vector0 at the actual IDIV with the fault operands/stack
and evaluator cursor verified. Each execution uses a fresh CPU: Unicorn can
retain a pending fault and raise double-fault on a reused instance. The oracle
stops at the divide-error interrupt; it does not emulate OS exception recovery.
Original surrounding dynamic expressions, gameplay and nonnumeric inputs are
not executed or mocked as evidence. A floor-division expectation fails an
executed negative non-integral pair.

Eight new tests cover exact code isolation, opaque/invalid contexts, boundary/
zero/overflow literal storage without folding, unsupported extents, all six
expression types/both roles/scopes, readable output, lossless source programs,
late-invalid refusal before all outputs/reporting and immutable repeats. The
optional original fixture walks source-program token spans independently with
the pinned reader registry and checks all15 stored division words/extents and
annotations. CI skips that fixture when the player's local project is absent.

## Numeric remainder token (schema17)

Exactly four-byte `0x0A00` tokens receive `integer_operation` with `name: remainder`,
`operand_order: left_remainder_right`, `bits: 32`, `signed: true`,
`quotient_rounding: toward_zero`, `nonzero_result_sign: dividend`,
`zero_divisor_result: left_operand`, `overflow: x86_divide_error`,
`exception_recovery: unknown`, numeric `required_operand_tag: 0`,
`other_operand_tags: unknown` and `evidence: cnc_runtime_operator_table`.
For a nonzero divisor the result is left - trunc(left/right) * right: -7 % 3
returns -1 and 7 % -3 returns 1. For divisor zero this handler returns the left
operand unchanged. INT32_MIN % -1 raises the CPU divide-error exception, even
though its mathematical remainder is zero. OS/process recovery is unverified.
This is a numeric runtime capability: independent source walks find **no such
tokens in this original project**, so it establishes no new observed gameplay.

The annotation never selects actual operand tags/contexts, validates grammar or
precedence, folds constants or evaluates dynamic expressions. There is no prefix
annotation. Short/extended recognized tokens fail exit2 before JSON/text/bundle
writes or reporting; other codes retain their storage rules. Prior raw fields,
annotations and ordering are preserved. `coverage.expression_integer_remainder`
marks supported decoding, not presence in the input; `expression_evaluation`,
`parameter_semantics` and `opcode_semantics` remain false. Readable EXPRESSION JSON
includes the operation for inputs containing it. Older immutable bundles must
be moved aside before regeneration; other research components stay unchanged.

### Original instructions and independent execution

Original executable SHA256 remains
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`.
Evaluator0x42a42e selects table0x41b574+(code>>8)*2: `0x0A00` selects pointer
0x41b588 to handler0x42a547. It swaps EAX/right with ECX/left, uses CDQ to
sign-extend the dividend, tests ECX and skips IDIV/MOV EAX,EDX on zero. Otherwise
IDIV ECX at0x42a54d computes the remainder, MOV EAX,EDX returns it, and SUB DX,DX
sets the numeric result tag. INT32_MIN/-1 traps before the result move/tag clear.
These binary-specific addresses are evidence, not exporter dependencies; no
original machine bytes/assets/generated metadata are committed or published.

Private agent evidence `data/furries/expression-remainder/runtime_oracle.py`
executes the actual handler and complete evaluator independently via Unicorn2.1.4.
49 signed-boundary pairs, four explicit signed rounding pairs and512 seeded pairs
give1130 executions:1128 checked returns and two vector0 overflow exceptions at
the actual IDIV. Results, low16 numeric tags and balanced return stacks are checked;
evaluator cursors and trap operands/stacks are checked in both outcomes. All seven
boundary dividends with zero divisors are covered. Each execution has a fresh CPU.
A Python-modulo expectation fails an executed opposite-sign pair. No dynamic
functions, original surrounding expressions, gameplay or nonnumeric inputs are
executed/mocked; exception recovery is not emulated.

Eight exporter cases cover exact-code isolation, opaque contexts, signed/zero/
overflow literals without folding, unsupported extents, all six expression types
in both record roles and scopes, readable annotations, lossless programs, immutable
repeats and late-invalid refusal before all outputs/reports. The optional original
fixture independently walks source spans with the pinned reader registry and
confirms absence of remainder tokens and annotations. Synthetic inputs exercise
positive annotations; CI skips only the local-original fixture when absent.

## Expression control tokens (schema18)

Exactly four-byte `0xFFFF`, `0xFEFF` and `0xFDFF` tokens receive an
`expression_control` annotation. `0xFFFF` has `operation: recursive_operand`,
`inner_start_token_offset: 4`, `inner_return_cursor: unconsumed_evaluator_stop`
and `dispatch_return_cursor: after_stop_token`. The inner evaluator returns
with EDI pointing at its stopping token; the outer operand dispatcher then
advances EDI by that token's stored length. This permits nested numeric/string
operands in isolated runtime probes. `other_operand_tags` and
`delimiter_pairing` remain `unknown`; evidence is `cnc_runtime_dispatch`.

`0xFEFF` and `0xFDFF` both have `operation: evaluator_stop`,
`return_cursor: unconsumed`, `delimiter_role: unknown` and evidence
`cnc_runtime_evaluator`. This establishes their control flow, without claiming
which delimiter closes a grouping or separates function arguments. Neither is
the zero word that terminates the **storage** token list: the exporter continues
preserving subsequent stored tokens after both runtime stop words. It does not
pair markers, check expression grammar or evaluate any expression. The zero
storage terminator also stops the runtime evaluator; unmatched recursion and
its subsequent length read were not executed as valid runtime behaviour. Unbalanced
markers remain exportable storage. Control words in the opaque suffix after
the first zero storage terminator remain opaque.

Other codes stay unchanged. Unsupported extents of these three recognized
control tokens fail exit2 before JSON/text/bundle output or fault reporting.
`meaning: unknown`, all previous raw fields, order, literals, arithmetic,
references and editor-group annotations remain unchanged. The only additions
are `expression_control`, `coverage.expression_control_tokens`, versions and
the readable coverage sentence. `expression_evaluation`, parameter/opcode
semantics and behaviour remain false. Preserve the older immutable research-v1
bundle before regenerating; its contents are never silently replaced.

### Original-runtime evidence

The local FF2xmas.exe SHA256 is
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`.
Dispatcher0x42a474 sign-extends both token bytes. For `0xFFFF`, type-1 table
pointer0x41a384 ->0x41b2b8, entry0x41b2b4 selects handler0x42a4ac. The handler
advances EDI by4, calls evaluator0x42a42e and returns. The dispatcher subsequently
reads the returned cursor's length at+2 and advances EDI by that extent.
Evaluator comparisons0x42a449 and0x42a450 explicitly stop on `0xFEFF`/`0xFDFF`
without advancing the cursor. These addresses refer to the original CnC runtime,
not a newer SDK dialect. Original instruction bytes are not committed.

Independent Unicorn2.1.4 evidence in private agent state
`data/furries/expression-control/runtime_oracle.py` executes the real handler,
dispatcher and complete evaluator: 177 boundary/seeded numeric pairs with both
stop words, nested arithmetic/prefix signs, depths1/2/4/8/16/32, and both
numeric/string result tags. Every run checks the result/pointer, low16 tag,
cursor, return address and balanced stack. Direct handler/evaluator probes
leave stops unconsumed; dispatcher probes consume them. Poison tokens after
stops establish that the inner evaluator actually stops. Grouped `(7+3)*5`
returns50; ungrouped `7+3*5` returns22. These are isolated execution probes,
not a complete precedence specification or original gameplay evaluation.

A separate source-program walk, with pinned KlikBack expression traversal,
verifies all126 original control tokens: four `0xFFFF`, 105 `0xFEFF`, 17 `0xFDFF`,
all with extent4. Each stored original token is executed with independent
numeric probes, not its original dynamic operands. Total1906 executions pass.
An ungrouped-result negative expectation fails the grouped runtime probe; a
consumed-stop cursor expectation fails a direct evaluator probe. Delimiter
pairing, function argument roles, dynamic/global evaluation, nonnumeric
operators and gameplay remain unresolved. Local tests separately verify source
words/extents, lossless program reconstruction, both event roles/all six
expression parameter types/scopes, unbalanced storage, suffix isolation,
strict malformed-input refusal and immutable bundle repeats. CI skips only
user-supplied original fixtures; no original content is committed or published.


## Closed ungrouped integer constants (schema 19)

This describes the initial schema19 subset; schema20 extends it to the closed
recursive operand shapes documented below.

Every `expression_storage` adds `constant_integer_evaluation`. This is a
conservative evaluation of the complete stored token stream, starting after
its opaque prefix and ending at its first zero code. It evaluates only one or
more exact integer literals, separated by the supported binary numeric
operators (add, subtract, multiply, divide, remainder). Each operand may have
one prefix minus. All token annotations, raw bytes, offsets, references and
opaque prefix/suffix remain unchanged; no tokens are substituted or folded.
The new result also appears inside the existing JSON-escaped EXPRESSION line.

The original evaluator compares **raw signed16 operator codes**, pushing an
operator only when its code is greater than the pending one. For this bounded
positive-code subset the priority is thus `0x0A00` remainder > `0x0800` divide >
`0x0600` multiply > `0x0400` subtract > `0x0200` add. Equal codes associate left.
These are distinct priorities, not conventional groups: `20 * 7 / 3` gives 40
(`20 * (7 / 3)`), `20 / 7 remainder 3` gives 20 (`20 / (7 remainder 3)`), while
`20 / 3 / 2` gives 3. Prefix minus is consumed by the operand dispatcher before
binary evaluation. Every intermediate numeric result uses 32-bit wrapping;
division truncates toward zero, remainder follows the dividend's sign, and
zero divisors give quotient 0 or the unchanged dividend for remainder.

- `status: value` adds `value_signed_i32`, `value_raw_u32`, numeric `result_tag: 0`
  and `evidence: cnc_runtime_evaluator`.
- `status: cpu_exception` records `fault: x86_divide_error`, vector 0, the pending
  `operator_token_id`, and unknown exception recovery. INT32_MIN divided by or
  remainder -1 traps; no result is invented. The pending operator is identified
  after prior reductions, which can wrap or change its operands.
- `status: unsupported_tokens` lists every unsupported storage `token_ids`.
  String literals, dynamic/object/function operands, unknown operators and all
  recursive/stop tokens are excluded from this slice, even when part of the
  stream appears constant. No original dynamic operands are mocked.
- `status: unsupported_shape` retains empty streams, missing operands,
  adjacent literals, repeated prefix minus and incomplete operator sequences.
  This means outside the supported grammar, not proven invalid in the original.

The entire stream is checked for supported tokens and shape before arithmetic.
An unsupported tail cannot produce a speculative value or divide-error claim
from a supported-looking prefix. Unsupported forms and recorded CPU exceptions
are ordinary research output, never exporter faults or private fault reports.
Existing malformed literal/operator extents still refuse all output with exit2.
No expression prefix, parameter role, event execution, comparison, game-state
change, string/grouped arithmetic or general grammar is inferred. New
`coverage.constant_integer_expressions` is true; general
`coverage.expression_evaluation` and parameter/opcode/behaviour coverage remain
false. Results are expression-level evidence, not a playable behaviour spec.

Independent local execution uses unmodified instructions from FF2xmas.exe
SHA256 `f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`:
evaluator `0x42a42e`, raw-code comparison `0x42a457`, operand dispatcher
`0x42a474`, and operator table `0x41b574`. Unicorn2.1.4 runs all 25 ordered
operator pairs on asymmetric/rounding/zero/boundary triples with eight prefix
sign combinations, 1,024 seeded streams of up to 16 operands, and four focused
priority/association probes. All 3,490 eligible original expressions additionally
execute their exact source bytes: in this project they are single literals,
not compound arithmetic. All other 378 original expressions remain unresolved.
In total 5,718 executions pass: 5,667 normal results with numeric tag, cursor and
balanced stack checks, plus 51 divide errors with vector, IDIV address and fault
operands verified. This proves compound capability on synthetic streams and
literal-only results in the project; it does not prove OS exception recovery or
execute dynamic, nonnumeric, grouped expressions or gameplay.

Synthetic tests cover raw-code priority, equal-code associativity, wrapping
intermediates, unary boundaries, signed rounding/zero/overflow, fault operator
identity, whole-stream refusal, opaque tails, a long iterative stream, every
expression parameter type in both record roles/scopes, readable results,
lossless reconstruction, immutable bundle repeats and malformed late inputs
before JSON/text/bundle writes or reporting. Original-only tests independently
classify complete source streams and check every eligible value/raw word and
unresolved remainder. CI skips that private fixture without `FF_TEST_PROJECT`.

## Closed recursive integer constants (schema 20)

`event-dump/20` extends `constant_integer_evaluation` to a bounded recursive
numeric subset. At an operand position, an exact four-byte `0xFFFF` enters an
inner evaluator. After a complete inner numeric expression, either exact
four-byte stop (`0xFEFF` or `0xFDFF`) returns its value; the outer dispatcher
consumes the stop. One optional prefix minus applies **after** the inner return.
The same five numeric operators and raw-code priorities apply in every invocation.
For example, `FFFF 7 + 3 FEFF * 5` returns 50, and a prefix minus before FFFF
makes the result -50. Mixed stop words and further nesting are supported.
These are proven execution shapes, not a general delimiter-pairing or function
argument grammar. Stops outside recursive operands, empty or unclosed inner
expressions, adjacent operands, repeated prefix signs and trailing operators
produce `unsupported_shape`. A zero storage terminator is never treated as an
implicit inner stop: the original dispatcher would read its following extent,
whose safety and meaning are unproven. Dynamic, string and function tokens still
refuse the whole stream as `unsupported_tokens`; no supported prefix is evaluated.

The exporter first validates the **whole** stream and builds an iterative
execution plan, then executes arithmetic. This handles deep input without
Python recursion. The plan reduces a pending outer operator before reading the
next operand when its priority requires it, matching the original evaluator.
It does not eagerly evaluate all inner expressions first. With competing divide
errors, this determines which `operator_token_id` faults. Normal results,
32-bit wrap, signed rounding, zero-divisor behavior and explicit CPU exceptions
retain their previous schema. `coverage.recursive_integer_constants` is true;
general expression/parameter/opcode/behaviour evaluation remains false.
All raw bytes, token IDs, annotations, references and opaque prefix/suffix stay
preserved; readable text uses the existing whole-expression result field.
Recorded runtime exceptions and unsupported research forms never invoke the
optional private exporter fault reporter. Malformed token extents still exit2
before JSON, text, bundle writes or reporting.

Independent local Unicorn2.1.4 execution uses the same unmodified original
FF2xmas.exe (SHA256 recorded above), evaluator `0x42a42e`, dispatcher `0x42a474`,
recursive handler `0x42a4ac` and numeric operator handlers. Both stops, prefix
signs, nesting depths 1 through 64, all 25 ordered operator pairs with asymmetric,
signed, zero and overflow probes, competing inner/outer faults and 1,024 seeded
nested streams are exercised. All 7,754 executions pass: 7,604 normal results
with numeric tag, exact return cursor and balanced stack checked, plus 150 divide
errors with vector, IDIV instruction, fault operands, exact pending token ID
and retained return address checked. Of these, 3,490 runs use eligible original expression bytes unchanged;
all are still single literals. The original's four recursive markers and 122
stop words occur only in streams containing unsupported dynamic/function tokens,
which remain unresolved. No new original compound result, OS exception recovery,
nonnumeric behavior, function grammar or gameplay execution is claimed.

Nine new tests cover both stops/mixed nesting, prefix and numeric boundaries,
priority and fault order, complete-stream refusal, 4,096 iterative nested
operands, opaque tails, all six expression parameter types/both roles/scopes,
readable/lossless output, immutable bundle repeats, late malformed controls
before every output/report and independent original control-word traversal.
Original statuses remain 3,490 values / 378 unsupported streams. In 103 of the
unsupported streams, `token_ids` now excludes the newly supported control words;
the remaining unknown tokens still prevent evaluation. All other fields/results
and text remain unchanged apart from version/coverage and the coverage sentence.
Existing immutable bundles must
be retained separately before regenerating the changed events/manifest files;
all other 640 component files stay byte-identical. Media schema/bytes do not change.

## Position coordinate inputs (schema 21)

`event-dump/21` adds `position_coordinate_storage` to the four supported position
parameter layouts (types 9, 16, 18 and 21), alongside their unchanged reference
annotations. It retains the little-endian flags word at payload+2 and the X/Y
words at payload+4/+6, each with its offset, unsigned bits and signed 16-bit
view. Payload offsets exclude the four-byte size/type header. Flags are raw:
no complete flag dictionary, direction, hotspot, image handle or selected object
is decoded. All original parameter bytes, opaque tails and reference candidates
remain unchanged. Readable text adds a separate `POSITION_COORDINATES` line.

`word_usage` is `absolute_xy` only for the two externally established source
sentinels 0xFFFE/0xFFFF; every other reference is `context_dependent`. No source
slot encoding is assumed to be a runtime address. Every annotation retains
`runtime_resolution: false`, with evidence `cnc_position_helper_coordinate_inputs`.
The exporter emits coordinate **inputs**, not a resolved world position or
an initial/player spawn. `coverage.position_coordinate_storage` is true;
`position_resolution`, general behaviour and arena geometry remain false.

The original FF2xmas.exe helper `0x42a2a6` reads words+4/+6 into AX/BX on its
negative-reference path (`0x42a2d8`), even when flags would alter a relative
position. With helper mode BX=0, it returns those bits unchanged, DX=0 and
carry set. In its positive-reference path it calls the original selector
`0x426c0f`; after successful selection, the cartesian/no-hotspot path adds the
same words at `0x42a393` to object position words+0x3E/+0x42, wrapping at 16 bits.
Flag bit 0 bypasses these additions; flag bit 1 introduces image-dependent
hotspot work. Their complete meanings, noncartesian path, selection remapping,
other helper modes/clipping, direction/RNG and containing event opcodes are
outside this slice. The signed view matches the helper's signed bounds
comparisons, but the exporter does not run those comparisons.

Independent local Unicorn2.1.4 executes the unmodified helper and its real
cached-state selector against the original binary SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`.
No instruction, import or selector is replaced. Seven signed boundaries on both
axes, both absolute sentinels with six flag words, three selected origins and
512 seeded inputs exercise direct return and wrapped relative addition.
All 4,286 executions pass with coordinate bits, DX, carry, balanced stack,
return address, restored ESI/EDI and unchanged input bytes checked.
A deliberate positive-seven expectation fails on actual returned negative-seven
bits. The state is synthetic: cached selection establishes arithmetic capability,
not the game's actual selection/global mapping or event execution.

All 1,263 original position parameters supply their actual coordinate words to
two **synthetic contexts** in that proof: forced absolute sentinel and forced
cartesian/no-hotspot cached selection. The original reference/flags are changed
for those probes; no actual original position result is claimed. Separately,
direct reads from original frame/global program spans verify every exported
word and signed value: 1,150 type9, 110 type18 and three type16 parameters.
The original flag words are 10 (570), 2 (30), 6 (80), and 8 (583); every original
reference remains context dependent. Type21 has synthetic storage tests only.
Pinned KlikBack's position remapper independently preserves the flags/X/Y bytes
while editing reference/cache fields. This is corroboration of storage offsets,
not a full runtime compilation or opcode witness.

Eight tests cover signed/unsigned boundaries, both axes, all four shapes, opaque
flags/encodings, frame/global and condition/action scopes, lossless programs,
readable values, unchanged references, external remapper agreement and immutable
bundle repeats. A late short supported parameter (even with complete coordinate
words) exits2 before JSON/text/bundle writes or reporting. Ordinary bad inputs
and unknown position results never invoke the existing optional private fault
reporter. CI runs synthetic tests with the pinned external reader and skips the
original-span fixture unless `FF_TEST_PROJECT` is supplied. General placement,
arena geometry/spawns and observed gameplay remain separate M0 work.

## Type23 comparison-prefix inputs (v22)

`event-dump/22`, schema22 adds `comparison_prefix_storage` only to type23
parameters, in either record role and both frame/global programs. The unchanged
expression storage, prefix word, token bytes, suffix, and containing opcode remain
available. No new inference is made for types15/22/45/52/53 or unknown types.

The original parameter getter dispatch at0x42775f reads the parameter type at+2
and jumps through table0x41af64. Entry23 selects0x4277ca: it saves the word at
parameter+4 (payload+0), evaluates from parameter+6 through0x42a417, restores
that word into BX, increments BX with16-bit wrap, and clears carry. Thus
`getter_bx_on_normal_expression_return_raw_u16` is `(prefix+1)&0xFFFF` and
`getter_carry_on_normal_expression_return` is false. These are explicitly normal
return inputs; they do not promise that a dynamic expression returns or a CPU
fault recovers. Unknown prefix words, including0xFFFF→BX0, are retained.

`conditional_integer_consumer` assumes execution reaches the original signed
integer comparison path. At0x4284cf the caller's EAX is saved as the left value,
the right parameter is evaluated, prefix at parameter+4 is loaded and masked
with0x7FFF at0x4284d9..0x4284dd, and `cmp ecx,eax` compares left versus right.
The unmodified table0x41b1f0 maps indices0..5 to:

- 0: equal, handler0x428502 (JE)
- 1: not_equal, handler0x42850d (JNE)
- 2: less_or_equal, handler0x4284f7 (JLE)
- 3: less, handler0x4284ec (JL)
- 4: greater_or_equal, handler0x428523 (JGE)
- 5: greater, handler0x428518 (JG)

Ordering is signed32, including overflow-aware x86 comparisons across extreme
operands; equality uses all32 bits. Prefix bit15 is recorded as
`opaque_high_bit_raw_u16`: its purpose is unknown even though this consumer masks
it away. Indices6..32767 have status `outside_proven_table` and null operation.
They remain valid storage, never guessed aliases or errors. This exporter does
not execute the original out-of-table dispatch or infer its behavior.

The annotation always has `runtime_resolution: false`, null `left_value` and
null `condition_result`. Type23 storage alone does not prove that the containing
opcode uses this particular numeric consumer, that an operand is numeric, that
a global object resolves, or that an event condition succeeds. The original also
has a string comparator path; string order, imports, result tags and high-bit
roles are outside this slice. Even an independently supported closed integer
right expression is not a whole-condition evaluation.

Readable output adds a separate `COMPARISON_PREFIX` JSON line after the unchanged
`EXPRESSION` line. Previous lines/raw annotations are preserved. Coverage adds
`comparison_prefix_inputs: true`; general parameter/opcode semantics and
expression evaluation remain false. Invalid supported expressions still fail
before JSON/text/bundle output or fault reporting. Existing unexpected-fault
reporting is unchanged; no private endpoint or original content is committed.

Independent original source traversal and the pinned reader's token walk verify
all1400 type23 parameters: all conditions, prefixes0:578/1:60/2:92/3:461/5:209;
1378 closed integer right expressions and22 dynamic expressions. No prefix4 or
high-bit case is observed in this project; those remain synthetic capabilities.

Unmodified FF2xmas.exe (SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`)
in Unicorn2.1.4 executes the complete parameter getter for every65536 prefix
word and the1378 original constant parameters. Signed consumer execution includes
588 boundary combinations (six indices, both high-bit values, seven-by-seven
signed operands),6144 seeded comparisons and seven left probes against each
of the1378 original closed right expressions. Including an executed wrong
unsigned expectation,83293 executions verify returned values/tags, BX wrap,
carry, branch destinations, parameter bytes, return stack, preserved registers
and unchanged mapped executable bytes. Dynamic original expressions are never
executed. Getter dispatch and calls/evaluator are original instructions; numeric
consumer stops before condition bookkeeping at0x4294a2/0x4294b1. No instruction,
import or callback replacement, caller condition dispatch, string comparison,
actual left state, event activation or gameplay execution is claimed. Proof and
original data stay outside the repository in agent state.

## Immediate scalar parameter getter inputs (v23)

`event-dump/23`, schema23 adds `scalar_getter_storage` only for the exact
parameter types below. These are conditional inputs/returns of the original
runtime's generic parameter getter, not inferred meanings of event opcodes.
Both frame/global programs and condition/action records receive the annotation.

The original FF2xmas.exe dispatch at `0x42775f` zero-extends parameter WORD+2
(the type) into EBX and jumps through table `0x41af64`:

- Types **3, 4, 5, 10, 12, 14, 15, 17, 26, 32, 34** select `0x42779d`, which
  executes `movzx eax, WORD [eax+4]; sub bx,bx; ret`.
- Types **2, 24, 29** select `0x4277a5`, which executes
  `mov eax, DWORD [eax+4]; sub bx,bx; ret`.

`payload_offset: 0`, `stored_bits` and `stored_raw_unsigned` expose exactly
that WORD/DWORD at parameter+4. `opaque_suffix_hex` preserves every following
payload byte; the complete prior `payload_hex` remains unchanged. The WORD
case returns EAX in 0..65535, including 0xFFFF as 65535, without sign extension.
The DWORD case transports all 32 bits unchanged. Neither path establishes the
caller's signedness, units, flags, player/index meanings or sentinel conventions.

`conditional_getter_return` explicitly assumes execution reaches the original
parameter-getter dispatcher. Under that assumption `eax_raw_u32` is the stored
value, `extension` is `zero_extend` or `none`, BX is zero and carry is clear.
DX is **preserved incoming data**, not a newly supplied numeric/string value
tag: unlike the expression-literal handlers, these getters do not write EDX.
`caller_interpretation: unknown` and `runtime_resolution: false` apply even to
single literal-looking values. There is no caller/opcode selection or condition
result, allocation, timer, player/global or gameplay execution.

Type26 action frame-target storage coexists unchanged with this annotation;
WORD transport does not resolve its CnC runtime destination. The pinned external
reader classifies type15 as expression storage. That prior token view is retained,
but the actual original **generic getter** table entry for type15 transports
only its prefix WORD. The views have separate assumptions: the token view must
not be promoted to proof that this getter evaluates type15's expression. No
original type15 occurs in this project. The other unobserved types likewise
represent synthetic runtime capabilities only. No newer Clickteam table is used.

A supported scalar with fewer than two/four payload bytes fails with InputError
before standalone JSON/text or bundle output; malformed input is exit2 and
never fault-reported. Existing expression and other parameter checks remain.
Unknown types retain their opaque payloads and receive no getter annotation.
Readable text adds `SCALAR_GETTER` after the unchanged PARAM and existing
annotation lines. Coverage adds `immediate_scalar_getter_inputs: true`; general
parameter/opcode semantics and dynamic expression evaluation remain false.

Independent absolute source traversal verifies all **793** original parameters:
types2:7, 10:197, 14:16, 17:246, 26:2, 29:307, 32:18. Every exported stored value,
suffix and existing row/record/parameter byte reconstructs exactly. No other
types are silently assigned this getter behavior.

Local private execution evidence uses the unmodified original executable
SHA-256 `f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`
in Unicorn2.1.4. All65536 WORD values execute through the real dispatch/shared
WORD handler. Every exact table entry additionally runs unsigned bit boundaries
with three distinct incoming DX values, 512 seeded values per type, and every
original parameter runs with all three incoming DX values: 75,420 complete
dispatch/getter executions in total. Checks cover EAX,
full EBX/EDX, carry, ECX/callee-preserved registers, return/stack, complete input
bytes and entire mapped executable bytes. A wrong sign-extension expectation
fails on actual EAX0x0000FFFF. No instructions/imports/callbacks are substituted;
no parameter caller, live event dispatch or gameplay is executed. Proof scripts,
original bytes and exports stay private/ignored outside the repository.

## Parameter address getter inputs (v24)

`event-dump/24`, schema24 adds `address_getter_storage` for exact original
dispatch entries, in both frame/global programs and condition/action records.
This documents a generic getter's conditional address return, not the containing
opcode's meaning or its eventual use of that address.

In original FF2xmas.exe, dispatch `0x42775f` zero-extends parameter WORD+2 into
EBX and jumps through `0x41af64`:

- Types **6, 7, 8, 9, 11, 13, 18, 19, 20, 21, 25, 27, 28, 30, 31, 33, 35,
  36, 37, 38, 39** select `0x427784`: `sub bx,bx; ret`. EAX still points to
  the **parameter header**, including its size/type words, not to payload+0.
- Type **40** selects `0x427791`, verifies EBX==40, then executes
  `lea eax,[eax+4]; sub bx,bx; ret`. EAX points to the **payload**, with ordinary
  32-bit wrapping address arithmetic. It does not dereference or search it.

`conditional_getter_return` explicitly assumes execution reaches this original
parameter-getter dispatch. It records `parameter_relative_offset` 0 or 4, target
`parameter_header` or `parameter_payload`, and the unknown runtime EAX address.
No executable/host address is invented from a source-file offset. BX is zero,
carry clear and DX preserves incoming data, not a newly created numeric/string
tag. `stored_bytes_from_target` counts bytes retained in this one stored
parameter from that offset; it is **not** a runtime memory accessibility bound
or a guarantee that the caller reads only those bytes. For an empty type40
payload it is zero, while address transport still succeeds.

The getter itself does not load an audio handle, resolve an object, extract
coordinates, activate a group, parse text, check a NUL terminator or evaluate an
expression. Existing audio/position/group storage annotations coexist unchanged;
those identify separate stored fields, not EAX scalar returns. Type40 is not
assigned string content/encoding/lifetime semantics merely because its target
is the payload. Type1 has a state-dependent handler and is excluded; type16
calls another helper and is excluded. No entries beyond the checked table range
0..40 are extrapolated. Unknown types retain their raw storage.

`caller_interpretation: unknown`, `payload_dereferenced_by_getter: false` and
`runtime_resolution: false` remain explicit. The coverage key
`parameter_address_getter_inputs` is true, but general parameter/opcode semantics
and dynamic expression evaluation remain false. Readable output adds
`ADDRESS_GETTER` after prior PARAM/annotation lines. The original payload and
all prior JSON fields/text lines remain unchanged. No new minimum payload length
is inferred: these paths inspect only the already-validated parameter header.
Existing independently supported audio/position/etc. layouts still require their
own extents. Malformed storage remains exit2 before JSON/text/bundle writes or
fault reporting; unexpected faults retain the existing detached optional reporter.

Independent absolute source traversal verifies all **2,502** original parameters:
types6:870, 7:21, 9:1150, 13:122, 18:110, 19:29, 38:41, 39:159. All header sizes,
types, payload bytes and row/record/program reconstruction agree. Type40 and the
other absent types are synthetic capabilities, not original gameplay observations.

Private runtime proof executes the unmodified FF2xmas.exe SHA-256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`
in Unicorn2.1.4 through the complete dispatcher/getters. Exact table entries
0..40 are independently inspected. The 20,421 executions cover 1,584 cases of
22 types/six empty or arbitrary payloads/four aligned and unaligned addresses/
three incoming DX patterns, 66 address-wrap cases, 11,264 seeded cases and every
original parameter with three incoming DX patterns (7,506 runs), plus one wrong
payload-pointer expectation that fails. The wrapped type40 result is an unmapped
zero address, demonstrating address transport without payload dereference.
Checks cover EAX/full EBX/EDX/ECX/callee-preserved registers, carry, full128-byte
stack/return, parameter bytes and entire mapped executable bytes. Original
instructions are unchanged; no imports/instructions/callbacks are substituted.
No caller/event/gameplay execution or runtime pointer resolution is claimed.
Proof scripts, executable bytes and generated exports stay private outside the repo.

## Type22 expression parameter getter inputs (v25)

`event-dump/25`, schema25 adds `expression_getter_storage` to **type22 only**,
for both record roles in frame and global programs. The original generic
parameter dispatcher `0x42775f` uses table `0x41af64`; exact entry22 selects
`0x4277c1`, **not** the similar code at `0x427788`. It calls `0x42a417`, then
executes `sub bx,bx; ret`. The wrapper preserves ESI/EDI and starts expression
evaluation at parameter+6 (payload+2). It skips the stored prefix WORD; that word
is not returned in BX. On normal expression return, EAX and DX come from the
evaluator, BX becomes zero and carry is clear. DX is an evaluator tag, unlike
the preserved incoming DX of the previously documented address/scalar getters.
The high half of EDX is not assigned a new meaning.

`conditional_normal_return` explicitly assumes both reaching type22's generic
dispatch and a normal expression return. `conditional_closed_integer_return`
uses the already proven closed integer evaluator subset: `status: value` adds
EAX raw32, DX0, BX0 and carry false. `cpu_exception` retains the divide-error
vector and unknown recovery, without any normal-return registers/flags. An
unsupported token/shape retains only its unsupported status; no dynamic/string
return or exception is guessed. The general normal-return contract is conditional,
not a promise that an unsupported expression reaches it. Opaque expression suffix
bytes and prefix remain unchanged in the existing expression-storage view.

This annotation does not establish that any containing opcode calls this getter,
what the caller does with its return, or the results of state-dependent expressions.
Type15's reader token view still coexists with its scalar getter; type23's prefix
transport/comparison view remains separate. No other expression-layout type is
assigned type22's runtime dispatch. `runtime_resolution` remains false and
`caller_interpretation` unknown. Coverage adds `type22_expression_getter_inputs`,
while general parameter/opcode semantics and dynamic expression evaluation remain
false. Text adds an `EXPRESSION_GETTER` line; prior lines/fields are preserved.
Malformed supported expression storage remains exit2 before JSON/text/bundle
output/reporting; unexpected failures retain the existing detached optional reporter.

Independent absolute source traversal finds **2,461** original type22 parameters:
2,172 action/289 condition; every stored prefix is zero. Of these, 2,112 are
closed single integer literals and 349 dynamic expressions remain unevaluated.
Original byte spans, literal bits, annotations and complete event reconstruction
are checked independently. Nonzero-prefix and compound/recursive capabilities
are synthetic proofs, not observations about original gameplay.

Private Unicorn2.1.4 proof runs the unchanged FF2xmas.exe SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`
through the **complete original dispatcher, exact type22 handler, wrapper and
numeric evaluator**. The 72,821 executions cover all 65,536 stored prefix words,
27 signed literal/incoming-DX probes, 405 arithmetic boundary pairs, four focused
recursive cases, 512 seeded recursive streams, 6,336 byte-exact original literal
runs (three incoming DX patterns) and one deliberately wrong prefix-transport
expectation that fails. 72,817 normal returns and four divide-error exceptions
are observed. Normal-return EAX/DX/BX/carry/stack/preserved registers, parameter
bytes and the entire mapped executable are verified; faults stop before exception
recovery. Each fault uses a fresh CPU afterwards, because Unicorn otherwise retains
pending exception state and a later divide error can appear as double-fault8.
No instruction/import/callback substitutions, dynamic/string evaluation, caller/
event dispatch or gameplay are executed. Proof scripts/original bytes/exports
stay private outside the repository.

## Type16 position parameter getter (v26)

`event-dump/26`, schema26 adds `position_getter_storage` to **type16 only**,
for both roles in frame/global programs. The original generic parameter dispatcher
`0x42775f`, table `0x41af64`, selects `0x4277ac`: advance from parameter header
by four bytes, clear BX, call the complete position helper `0x42a2a6`, shift EAX
left16, copy returned BX into AX, and clear BX. Thus on normal helper return,
**X occupies EAX's high word and Y its low word**, using raw16 coordinate bits.
DX is the helper's returned word, not a new numeric/string expression tag.
Caller interpretation and `runtime_resolution` remain unknown/false.

The final SUB clears carry, even if the helper returned carry clear for failure.
The getter does not preserve the helper's success/failure flag. Failed-helper
coordinate values remain unknown; no success is inferred from getter carry.
The general return layout is conditional on reaching this exact dispatch and
normal helper return, never a result for the containing action/condition.

With incoming helper BX0, a reference word whose **sign bit is set** takes the
helper's absolute branch: payload X/Y words at4/6 are returned unchanged, DX0,
then packed into EAX. `conditional_absolute_return` exposes these raw bits with
BX0/carry false. Flags and opaque tails do not alter this branch. This sign test
is conditional runtime input behavior, not a replacement for the prior stored
reference candidate/sentinel annotation or a global object mapping. With a
nonnegative reference word, the probe says `requires_live_object_state` and
contains no inferred EAX, coordinates, flags or status. Selected-object,
hotspot/polar, arena/spawn/caller/opcode semantics remain unresolved.

All three original type16 parameters are actions, with reference words4023,
402B,402A, flags8 and stored X/Y0. Their selector words at payload18 are17DA,
0866,0810. All require live object state; **none is evaluated in its original
context**. Independent raw-program traversal verifies these complete source
spans and the exporter retains prior reference/coordinate/raw payload views.
Coverage adds `type16_position_getter_inputs`; general parameter/opcode semantics
and position resolution remain false. Readable text adds `POSITION_GETTER`.
Existing strict type16 extent validation and detached optional fault reporter
remain: malformed storage exits2 before JSON/text/bundle output or reporting.

Private Unicorn2.1.4 proof executes the unmodified original executable SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`
through the **complete dispatcher, type16 getter, position helper and actual
cached-selection routines**. 34,755 executions include all32,768 negative
reference words, signed axis/flag boundaries,512 seeded axis/origin cases,
synthetic selected Cartesian origins with wrapping16 arithmetic, and failed
cached selections. Outcomes:33,578 absolute,662 Cartesian,515 failed-selection.
The three original coordinate/flag words are also exercised under explicitly
synthetic absolute/selected/failed contexts; their references/selector words
are changed for those contexts, never presented as original event execution.
Successful-helper carry1 and failed-helper carry0 are observed before the getter
packs coordinates; every normal getter return clears carry and BX. Return EAX
and DX where supported, preserved registers, return stack, parameter bytes and
the entire mapped image are checked (only supplied cache pointers and the helper's
one-byte cache flag are permitted changes in controlled relative contexts).
A deliberately reversed-axis expectation fails against the actual executable;
the initial oracle's reversed assumption was corrected before final evidence.
No instruction/import/callback substitutions, live caller/event/gameplay execution,
original object selection mapping, or real arena geometry are claimed. Proof
scripts/original executable/project/exports stay private outside the repository.

## Type1 state-dependent object parameter getter (v27)

`event-dump/27`, schema27 adds `object_getter_storage` to exact **type1**,
for both roles in frame/global programs. Original generic dispatch `0x42775f`,
table `0x41af64`, selects `0x42776a`. It tests a runtime byte at `0x41c866`;
the project bytes do not establish that byte's value. The exporter therefore
retains both conditional return contracts and `selected_branch:
requires_live_runtime_gate`, with `resolved_eax: null` and
`runtime_resolution: false`.

If the gate byte is zero, execution reaches `sub bx,bx; ret` at `0x427784`:
EAX remains the runtime parameter **header** address, BX0/carry clear, incoming
DX preserved. This branch does not dereference the payload. It is a conditional
address return, not a known object pointer or a new numeric/string value tag.

If the gate byte is nonzero, the getter calls the full selection helper
`0x426bcd` with EAX still the header. The helper reads the WORD at parameter+4
(**payload0**) into EDX. `selection_input_raw_u16` exports that word separately
from the existing editor `object_parameter_reference` at **payload2**. Neither
word chooses a branch or resolves an object by itself. No selector-offset,
qualifier, expected type, name or global mapping is inferred.

After a normal helper return, the getter copies helper ESI to EAX and restores
its saved incoming ESI. If helper carry was set, the final SUB returns BX0 and
carry clear. If helper carry was clear, STC returns carry set and leaves the
helper's BX unchanged. The EAX copy occurs in **both** paths; a failed helper
can yield a non-pointer value. `returned_pointer_validity: unknown` therefore
remains explicit. Active DX comes from the helper and has no inferred expression
tag; helper effects depend on live state. The contracts do not prove any containing
opcode calls this getter, nor that caller code uses the carry as success/failure.

All **974** original type1 parameters (690 conditions/284 actions; 760 frame/
214 global) retain unresolved runtime gates/EAX. Independent absolute traversal
checks both WORDs, all payload bytes and program extents: the words differ in
every original parameter, and all original first WORDs are nonnegative. Existing
editor candidates and raw record/parameter bytes are preserved. Coverage adds
`type1_object_getter_inputs`; general parameter/opcode/global semantics remain
false. Text adds `OBJECT_GETTER`. Existing six-byte minimum type1 payload validation
remains, including when the hypothetical inactive branch would not read it;
malformed storage exits2 before output/reporting. The detached optional private
fault reporter is unchanged.

Private Unicorn2.1.4 proof uses the unchanged original executable SHA256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`,
executing complete original dispatcher/getter/helper and cached-selector routines.
Its 73,563 successful executions cover every first WORD with gate zero,
all255 nonzero gate bytes with
controlled positive/negative cached selectors, signed boundaries, seeded payloads/
flags/counter wrapping, and every byte-exact original parameter under explicitly
supplied inactive/selected/failed contexts. These are not original runtime contexts.
Successful/failed helper carry is observed before the getter's conditional flag
handling; full return stack, parameter/image/cache/record bytes and preserved
registers are checked. Only explicitly supplied runtime data and actual helper
side effects are allowed; no instruction/import/callback substitutions occur.
A wrong failed-helper/getter carry expectation is rejected. The active FFFF
special-selector diagnostic fails the generic preserved-register expectation and
is excluded from the cached-selector proof; its live context is not inferred.
No caller/event/gameplay execution, actual object selection, arena or spawn
resolution is claimed. Proof scripts/original bytes/generated exports stay private.
