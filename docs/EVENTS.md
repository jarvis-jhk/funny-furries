# Event structure export v11

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
  fingerprints. `schema_version` is 14 and `exporter` is `event-dump/14`.
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
