# Frame layout structure v4

This M0 research slice exports frame headers and object-placement **storage**
as local JSON. It supplies the lossless placement tables needed for a later
arena decoder. Version 4 adds runtime-proven creation type inputs beside the existing
coordinate inputs and first-word/local-object-slot equality probes. It does not yet establish runtime
object references, final positions,
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
- `schema_version` is 4 and `exporter` is `frame-layout/4`. Existing raw fields,
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
  `meaning: unknown`. No word is labelled as a resolved object ID or final world position.
  Within `layout_document`, each record adds `object_slot_probe` and
  `coordinate_inputs` and `creation_type_input`, described below.
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
The research bundle automatically includes schema 4 and its component version;
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

## Creation coordinate inputs

Schema 3 adds `coordinate_inputs` beside each record's unchanged raw bytes and
object-slot probe. Its `x` and `y` entries retain `record_offset` (2 and 4),
`raw_u16` and a reversible `signed_i16` view of the little-endian coordinate
words. In particular a stored 0x8000 is retained as -32768; it is not a missing
coordinate. Neighbouring fields remain opaque. The context-free
`decode_placements` function still exports only storage.

The annotation has `meaning: creation_coordinate_inputs`,
`evidence: original_runtime_creation_coordinate_branch`,
`use_record_when_override_raw_u16: 32768`, and `runtime_resolution: false`.
The override marker applies to the creator's **argument**, independently for
each axis, not to the stored record word. An explicit argument replaces that
axis; a 0x8000 argument selects its record input. These are pre-initialization
coordinate inputs, not final live-object positions, rendered bounds, image
hotspots, player spawns or collision geometry. Neither pointer-slot order nor
object-slot equality establishes which records actually create objects.

Evidence is the local original FF2xmas executable (SHA-256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`):
creator 0x420AC1's coordinate branch at 0x420C28..0x420C54 compares the X/Y
arguments to 0x8000, reads record words at +2/+4 when needed, and copies them
into local coordinate words and object words at +0x3E/+0x42. An initial creation
caller at 0x40B73B supplies 0xFFFF8000 for both arguments before calling
0x420AC1 at 0x40B763. The runtime file-load path reads 32-byte records and
refreshes other fields; those instructions leave these two coordinate words
alone. The protected source's twelve placement blocks match the decompiled
source byte-for-byte. This evidence concerns the observed CnC executable and
storage dialect; newer MMF compiled placement formats are not substituted.

Independent local Unicorn 2.1.4 proof executes the unmodified coordinate branch
and the unmodified initial caller (including its 0x406020 record-index lookup),
stopping at the creator entry for the latter. Seven signed boundaries on both
axes, all four stored/overridden combinations, 512 seeded record/override cases
and all 7,968 original records produce 17,718 successful executions: 9,189
coordinate paths and 8,529 caller paths. Checks cover coordinate bits, local
copies, independent override selection, unchanged input/other object bytes,
stack and register preservation, and actual caller arguments. A deliberately
wrong positive-seven expectation fails after execution of stored negative-seven
input. No instructions/imports/creator are patched or replaced with stubs.

This is **partial instruction-path proof**, not whole original game execution:
allocation, definition selection, initial record filtering, movement and object
initializers, drawing and gameplay are not executed by this probe. The signed
view is a two's-complement representation; the creator itself copies 16 bits.
No actual initial-player/spawn position or post-initializer result is claimed.
General `placement_semantics`, `arena_geometry`, `spawns` and `behaviour` remain
false; only `placement_coordinate_inputs` coverage becomes true.

Tests exercise signed/raw boundaries, asymmetric axes, opaque neighbours,
record-word versus argument markers, aliases/reversed pointers/gaps, empty and
repeated blocks, both frame header extents, existing object probes, signed JSON,
immutable research-bundle repeats and a late short record before either output
or fault reporting. The optional original fixture independently reads every
coordinate word from each source span and preserves complete reconstruction,
repeat equality and the original fingerprint. Original instructions, content,
generated metadata and runtime proof outputs stay local and are not committed.


## Creation type inputs

Schema 4 adds `creation_type_input` to each stored placement record. It retains
`record_offset: 6`, the little-endian `raw_u16`, `type_raw_u8` (the low byte) and
`opaque_high_u8` (the high byte). The original creator reads this word and masks
it with 0xFF before passing it to its allocation dispatch helper. The high byte
is preserved, but no flag meanings are assigned. Neither a 0xFFFF word nor type
255 is labelled deleted/missing: storage encodings from another field do not
establish a type sentinel. Raw records and context-free decoding are unchanged.

`meaning: creation_type_input` and
`evidence: original_runtime_creation_type_dispatch` distinguish a proven runtime
input from a successful live-object type. Every annotation still says
`runtime_resolution: false`. `local_definition_comparisons` contains **every**
same-frame equality candidate from the existing `object_slot_probe`, retaining
`block_id`, `id`, `type`, `deleted` and a `type_equal` boolean. Missing slots have
an empty comparison list; deleted, differing and ambiguous candidates are not
filtered or chosen. Application-global bodies and other frames are not searched.
A matching header does not prove runtime definition selection or creation.

Evidence is the local original FF2xmas executable (SHA-256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`): creator
0x420AF3 reads the word at record+6, 0x420AF7 masks CX with 0xFF and the genuine
mixed-width call passes it to helper 0x420984. That helper branches on type <32
to a built-in table or >=32 to extension descriptor storage. Original
instructions were independently executed unmodified with Unicorn 2.1.4, using
observational stop hooks at the actual helper/callback entry or return. Original
built-in pointers were retained. Extension callback-address fields and definition
body offsets were synthetic **data** inputs; no callback implementation or import
was patched/stubbed. No allocation callback was executed.

All 65,536 word values, every missing extension-entry path, 512 seeded records
and all 7,968 original source records pass: 74,241 executions check masked type,
actual stack arguments, original helper target/zero-entry return and untouched
record bytes. An expected full-word type of 257 fails against the actual returned
selector 1. Protected/decompiled placement bytes agree. Every original low byte
matches exactly one live same-frame definition header: types 0/1/2/5/6/7/32/33/34;
1,722 records have nonzero high bytes. These counts are independently traversed
from source spans and the pinned reader, not inferred from exporter annotations.

In this executable, built-in allocation table entries for types 0 and 1 are zero;
5,090 original records take the helper's no-callback return when supplied as
synthetic creation inputs. This does **not** prove those placements are absent or
that backdrop rendering is unsupported: other original rendering paths and
initial creation filtering are outside this proof. Full allocation, definition
lookup, initialization, arena geometry/spawns and gameplay remain unresolved.

`coverage.placement_creation_type_inputs` is true. General placement semantics,
arena geometry, spawns and behaviour remain false. Synthetic tests cover all low
bytes with multiple high-byte patterns, opaque neighbours, missing/deleted/
mismatching/ambiguous header comparisons, frame scopes, aliases/gaps/reversed
pointers, both frame headers, empty/repeated blocks, lossless source bytes and
standalone/bundle immutable repeats. Late malformed placement storage fails
before output or fault reporting. Original-file tests separately verify every
word/header comparison; CI skips only that fixture without local game content.
