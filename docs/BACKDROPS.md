# Backdrop artwork, refresh inputs and placement probes v7

`tools/backdrop_dump.py` exports the artwork fields stored directly in ordinary
and quick-backdrop definition headers. It supplies image handles and editor fill
colors for a later arena decoder. Version 7 adds conditional quick-backdrop
fill dispatch and call inputs to frame-local placement candidates, alongside
rectangle inputs, refreshed record bytes, artwork and dimension candidates.
It does not render an arena or establish final placement coordinates, shape,
collision, spawns or runtime behavior. Effective ordinary-backdrop runtime
dimensions remain unresolved.

Use Python 3.10+ and the separately supplied KlikBack reader from
[EXPORTER.md](EXPORTER.md):

```
python3 tools/backdrop_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Output is ignored `export/<source-sha256>/backdrops.json`. It includes original
definition headers: never commit, publish or release it. Complete validation
precedes atomic replacement. Repeated exports with identical input/reader bytes
are byte-identical, input is never modified, symlink targets/directories are
refused and failed output writes preserve the old file and clean staging files.
Exit codes match the existing tools: 0 success, 2 invalid/unsupported input,
1 unexpected/write fault. Detached optional `FF_FAULT_REPORT_URL` reporting
includes only exporter version/platform and exception class. No endpoint, paths,
exception messages or original content enters reports or committed source.

## Contract

- `schema_version` is 7 and `exporter` is `backdrop-dump/7`. All previous raw
  fields and artwork annotations remain unchanged.
- Source and reader fingerprints match the project index. Image banks retain
  ordered segment IDs/offsets and occupied slot IDs; gaps, repeated/empty/missing
  banks remain distinct. Image IDs correspond to [IMAGES.md](IMAGES.md)'s PNG slots.
- Global-definition segments and frame-local definition blocks retain their
  order, IDs and offsets. Every object slot/type/global/deleted status is retained,
  with nullable `backdrop` for non-backdrop types. Missing, empty and repeated
  definition lists remain distinct.
- Type 0 (quick backdrop) and type 1 (backdrop) use their complete 68-byte header,
  retained as `header_hex` and SHA-256. `object_list_offset` is relative to that
  definition-list payload. All field offsets below are relative to the header.
  Nested object-data/icon blocks remain outside this export.
- The little-endian u16 at offset 54 is preserved as `image_word_raw_u16` in
  every decoded header, even when it is unused. Ordinary backdrops use it as
  an image handle. Their quick-fill/color bytes are left uninterpreted.
- For quick backdrops, byte 32's low nibble selects editor artwork: 0 solid,
  1 mosaic (tiled image), 2 gradient. Bit 0x10 selects horizontal gradients;
  otherwise they are vertical. The full byte is retained as `fill_raw_u8`.
  Other low-nibble values or bits outside 0x1F are unsupported and refused.
  The orientation bit is retained but not interpreted for solid/mosaic fills.
- Quick-backdrop colors at 24 and 28 are Windows COLORREF words. Each keeps
  its complete `raw_u32` plus RGB from its first three stored bytes; the high
  byte is preserved without being interpreted as alpha. Both words stay present
  for every fill kind, without claiming a mosaic uses those colors at runtime.
- `artwork.image_id` is populated only for ordinary backdrops and mosaics.
  Solid/gradient image words remain raw, without requiring bank membership or
  treating 0/0xFFFF as a picture. Every used image handle must occupy a bank slot.
  `image_bank_candidates` retains every matching bank's segment ID in source
  order, without selecting a runtime bank if more than one matches.
- Frame-local global-flagged definitions still contain their own headers and
  are exported from those bytes. No global/local definition resolution is made:
  the local image word can differ from the global one. Do not replace it with
  a guessed global match based on name or slot.
- Each decoded header adds nullable `quick_backdrop_dimension_inputs`, described
  below; ordinary backdrops have null rather than guessed image dimensions.
- Ordinary headers additionally receive `ordinary_backdrop_image_candidates`,
  described below; quick headers have null. The context-free `decode_header`
  does not add this field because it has no application image banks.
- `coverage` distinguishes header artwork/image handles/quick dimension inputs
  and ordinary image dimension candidates from runtime rendering,
  global resolution, geometry, spawns and behavior (all remain false).

## Evidence and limits

Pinned KlikBack `6e178b9470206f71871417dec852fbfa24cd01b9` provides external
editor-art evidence in `tgf/icon_census.py::source_handle` (header image word)
and `tgf/icon_generate.py::quick_backdrop_icon` (COLORREFs/fill/orientation).
The importer only uses the external container reader; our header decoder is
independently implemented. These icon helpers do not prove runtime tiling,
gradient rounding, opacity, collision, dimensions or draw order.

All 410 local-original backdrop headers are retained byte-for-byte: 352 ordinary
backdrops, 30 quick mosaic fills, 28 quick vertical gradients. All 382 used image
handles occupy the original bank. The original test separately reads each source
header, compares every image word with the external icon helper and samples the
external gradient icon's color endpoints. The 58 quick-backdrop color pairs
are independently compared with source bytes. No solid or horizontal gradient
appears in that original; synthetic fixtures cover those supported editor fields.

Synthetic tests also cover high COLORREF bytes, unused unoccupied image words,
global/local headers, local data blocks, deleted/non-backdrop slots, empty/missing
lists, gapped/repeated/empty image banks, unsupported flags and header sizes,
missing used handles, invalid late objects before any write, atomic failures,
symlink refusal and fault classification. CI skips the original fixture explicitly
unless a local `FF_TEST_PROJECT` is supplied; no assets are included in tests/CI.

Remaining M0 work includes display/text/extension artwork, global reference
resolution, event semantics, placement/arena geometry and spawns, and an
observation-backed behavior specification. Header artwork is one prerequisite,
not a playable engine or original-runtime/Windows/Deck proof.

## Quick-backdrop dimension inputs

Only type 0 headers receive `quick_backdrop_dimension_inputs`. `width` reads
the little-endian word at header offset 34; `height` reads offset 36. Each
retains `header_offset`, `placement_offset` (26/28), `raw_u16` and a reversible
`signed_i16` view. Zero, negative and sentinel-looking words are preserved: no
minimum, validity constraint or absent-dimension rule is invented. Neighbour
bytes, fill/image/color fields and raw headers stay unchanged.

The annotation says `meaning: quick_backdrop_dimension_inputs`,
`evidence: original_runtime_header_refresh_and_rectangle_paths`, and
`runtime_resolution: false`. `coverage.quick_backdrop_dimension_inputs` is true;
rendering/global resolution/arena geometry/spawns/behaviour stay false. The
context-free header decoder reads its supplied bytes without selecting an
application-global definition, live placement or effective runtime header.
A global-flagged local header can be replaced by runtime loading; this export
continues to describe that stored local header, not the selected global one.

Evidence is the local original FF2xmas executable SHA-256
`f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f`. Complete
helper 0x40F250 refreshes a placement from a supplied definition header. Its
type-0 branch copies header words +34/+36 to placement +26/+28 at
0x40F291..0x40F29D. Other fields are copied independently; the stored placement's
old dimension words are overwritten. Type 1 skips these dimension writes.
Loader 0x402638 invokes this helper after reading 32-byte placement records;
full file loading and global-definition selection are outside this proof.

The type-0 rendering-bounds path 0x405886..0x4058C8 sign-extends placement
+26/+28 and adds supplied left/top origins to form exclusive right/bottom
inputs. Quick fill function 0x4054B0..0x4054E3 sign-extends the same words,
adds supplied origins, subtracts one and takes signed minima with supplied
clip limits to form inclusive bounds. These arithmetic paths do not prove
that a backdrop passes culling, is painted or has rectangular collision.
Type-1 bounds instead call an image-metadata routine at 0x4058A9; the same
header offsets cannot establish ordinary-backdrop dimensions.

Independent local Unicorn 2.1.4 executes the complete unmodified refresh
helper followed by both unmodified arithmetic paths, with no instruction,
callback or import replacement. Seven asymmetric word boundaries, quick and
ordinary/non-backdrop helper branches, 512 seeded headers/origin/clip contexts
and all 410 original backdrop headers yield 2,310 executions: 1,070 helper
calls and 620 executions of each rectangle path. Destination bytes, untouched
header/record bytes, stack and preserved helper registers are checked; an
incorrect unsigned-65,529 expectation fails after executing signed-negative-7.
Runtime headers/placements/origins are supplied data, deliberately including
conflicting old placement dimensions. No drawing/import, actual header
selection, original gameplay or hardware execution is claimed.

All 58 original quick headers' words match independently walked absolute
source spans; the other 352 ordinary headers retain null dimensions. Synthetic
checks cover every supported fill, signed boundaries, unused ordinary words,
local/global differences, repeated/empty banks/lists, immutable standalone and
bundle repeats and late invalid fills/truncated definitions before output or
fault reporting. The research bundle records schema/component version 4. An
older different immutable bundle must be preserved before regenerating.
All original bytes, generated JSON and runtime proof data stay ignored/local.

## Ordinary-backdrop image dimension candidates

Each type 1 header in the complete document has
`ordinary_backdrop_image_candidates`. The existing header word at +54 is joined
by **bank slot**, never by a word inside the image record. All matching segment
IDs remain in source order. `status` is `single_bank_candidate` or
`multiple_bank_candidates`; even one candidate does not prove runtime selection.
The annotation has `meaning: ordinary_backdrop_image_dimension_candidates`,
`evidence: stored_image_metadata` and `runtime_resolution: false`.

Each candidate preserves `segment_id`, `image_id` (slot), `bank_offset` (relative
to bank payload), `record_bytes`, 24-byte `header_hex` and complete
`record_sha256`. `width` and `height` keep `image_record_offset` (10/12) and
`raw_u16`. These are the metadata words used by [IMAGES.md](IMAGES.md)'s image
exporter, independently compared with decoded PNG dimensions. No signed runtime
interpretation, world bounds, origin, hotspot correction or collision is added.
The ordinary header's quick-dimension words +34/+36 stay opaque/null.

A referenced ordinary image requires a complete 24-byte header; its u32 length
at +6 must equal the remaining record length. Zero/large metadata words, mode,
flags and other bytes are retained without interpreting them here. This is a
header-only view: it does not validate pixel encoding, enforce PNG pixel limits
or imply an unsupported image mode is renderable. The complete research bundle
also runs the existing strict PNG decoder before writing anything.

Metadata is decoded only for ordinary-backdrop references. Unused records and
quick mosaic images retain the previous artwork/handle contract; they do not
become ordinary dimension candidates. Missing used handles retain their existing
strict refusal. Repeated banks with conflicting dimensions keep every candidate;
global-flagged local definitions keep their own stored handle, even if an
application-global definition uses a different handle. No winner or fallback is
selected. Malformed referenced metadata fails with exit 2 before standalone or
bundle output and is not reported as a runtime fault. Unexpected/write faults
continue through the optional detached private reporter.

All 352 original ordinary headers have one image-bank candidate. Independent
absolute source reads verify its complete record/hash/header and width/height
words; decoded PNG IHDR/CRC/scanline readback agrees for every reference. All 58
quick headers retain null ordinary candidates. Synthetic checks cover conflicting
repeated banks, differing local/global handles, bank slots that differ from
record-internal words, empty bank/list gaps, header-only unsupported pixel modes,
raw dimension boundaries and late invalid metadata before both outputs/reporting.
Standalone/bundle repeats agree and an annotation-changing immutable bundle is
refused without mutation. Original data and generated outputs remain local/ignored.

The original ordinary bound path calls an image-metadata import; this slice does
not execute or replace it. Stored source metadata and PNG sizes are evidence for
candidate image dimensions, not a proof of live image selection, effective
rendering bounds, collision, arena geometry, spawn positions or behavior.

## Complete placement-refresh inputs

Each supported quick/ordinary header adds `placement_refresh_inputs` with
`meaning: backdrop_placement_refresh_inputs`,
`evidence: original_runtime_complete_header_refresh_helper`,
`runtime_resolution: false` and `dispatch_low_byte` (0 or 1). `writes` lists
conditional inputs in original helper execution order. Each item retains
`header_offset`, `placement_offset`, `bytes`, `raw_unsigned`, nullable
`and_mask`, and `written_unsigned`. Values are little-endian bit patterns;
no signed arithmetic, image-bank selection or collision meanings are added.

The complete original helper 0x40F250 first copies header dword +50 to placement
+12, then masks header word +42 with 0x0FFF and writes placement +6. Dispatch
uses the **low byte** of the unmasked word, independently of that 12-bit write.
The retained high-byte bits are opaque; never reduce the refreshed placement
type word to only its low byte. The meaning of the common dword +50 is unknown.

For quick backdrops it then copies header dwords +24/+28 to placement +16/+20,
and header words +32/+34/+36 to placement +24/+26/+28. The full +32 word is
copied, including its opaque high byte; the existing artwork annotation only
interprets the supported low-byte fill bits. Existing COLORREF and signed
quick-dimension views are unchanged. Ordinary backdrops skip these five writes.
Finally both kinds copy header word +54 to placement +8, **even for quick
solid/gradient fills whose stored image word is unused by the artwork view**.
An unoccupied unused word is not a missing asset or an invented sentinel.

These writes are conditioned on this stored header being supplied to refresh.
They do not establish which local/global body is selected, effective live
placement bytes, draw/collision order, geometry, allocation or actual spawns.
The exporter leaves unsupported/deleted/non-backdrop definitions null and does
not apply the writes to stored placement records. Existing fields and scopes
remain unchanged. `coverage.backdrop_placement_refresh_inputs` is true; all
runtime rendering/resolution/arena/spawn/behaviour claims remain false.

Evidence uses the same unmodified original executable hash recorded above.
Independent local Unicorn 2.1.4 runs the **complete** helper, including return,
for all 65,536 type words, 512 seeded supported headers, all 410 original
backdrop headers and an incorrect low-byte-only expectation probe. That yields
66,459 executions; full record byte equality, unchanged headers/instructions,
return stack and callee-preserved registers are checked. Unsupported dispatch
branches are executed only as oracle coverage, never promoted to exporter
support. Synthetic old placement bytes deliberately conflict with the header
inputs. Applying the exported writes to those supplied records agrees with
1,435 supported helper executions. No instruction/import/callback replacements
or original drawing/loading/header-selection/gameplay execution is used.

All original headers are independently checked against absolute source spans.
Tests cover every high-byte pattern, ordered writes, preserved opaque neighbours,
full fill words, unused image words, quick/ordinary write sets, differing global
and local headers, repeated banks, immutable standalone/bundle repeats, and late
invalid fill refusal before output/reporting. Outputs remain private/ignored;
existing optional detached fault handling and invalid-input exit codes remain.
An older immutable research bundle must be preserved before regenerating.


## Conditional placement refresh probes

Every frame adds `placement_refresh_probes`, one entry per placement block in
frame order, with actual `block_id`, `frame_offset`, payload SHA-256, complete
slot pointers/aliases and stored records. Missing blocks stay distinct from
empty ones. The strict lossless placement decoder from [FRAME-LAYOUT.md](FRAME-LAYOUT.md)
rejects malformed pointers, truncated storage or unreferenced records before any
standalone or bundle output. Context-free header and placement decoders are unchanged.

Each record retains its `id`, payload-relative `offset`, original `raw_hex` and
unsigned first word (`object_word_raw_u16`). That word probes every definition
list of the SAME frame by slot equality. Application globals and other frames
are never searched, including for a local header with its global flag set.
All u16 values use the same lookup; no new sentinel/encoded-reference assumption.
`status` is `missing_local_slot`, `single_local_candidate` or
`multiple_local_candidates`; all matches are retained without selecting a winner.

Each candidate gives `definition_block_id`, slot `id`, header `object_list_offset`,
`type`, `global`, `deleted`, nullable backdrop `header_sha256` and nullable
`conditional_record_hex`. Deleted and non-backdrop definitions keep explicit
`deleted_definition`/`non_backdrop_definition` status and a null preview. Live
backdrops have `conditional_backdrop_refresh` status. Their preview applies ONLY
the previously proven ordered header refresh writes to a copy of the stored
32-byte record. Every unwritten byte remains identical. Incoming record type
bits do not filter candidates: the supplied header overwrites that field.
The header hash/definition coordinates identify the matching artwork, fill and
image-bank candidates elsewhere in the same document without duplicating them.

`evidence` is `stored_word_local_slot_equality_and_conditional_header_refresh`
and `runtime_resolution` remains false on every record. These previews say what
the helper WOULD write IF this stored local header and record were supplied.
They are NOT effective runtime placements or a claim that the original loader
selects the local header, calls this helper for that placement, preserves these
coordinates until drawing, or creates a collision object. Global header selection,
ordinary image metadata lookup, collision, arena geometry and spawns remain open.
`coverage.local_placement_refresh_probes` is true; existing unsupported coverage
fields remain false. Schema 7 propagates into the immutable research bundle;
move an existing different bundle aside before regeneration.

Independent original-source traversal checks all 7,968 stored records, every
same-frame definition match, header hashes and conditional byte spans. All
5,090 backdrop previews (69 quick / 5,021 ordinary) were compared byte-for-byte
to complete unmodified original helper 0x40f250 calls in Unicorn 2.1.4, using
those stored records/headers as supplied DATA. Another 512 seeded conflicting
header/record pairs exercise the exported joins/previews. Every output byte,
return stack, callee-preserved registers, unchanged header and instructions
is checked. No original instructions, imports or callbacks were replaced;
actual loader selection, drawing, collision and gameplay were not executed.
All original content and executable proof data stay private and untracked.

Synthetic tests cover local/global flag differences, conflicting definition
lists, all candidate types, missing slots/unsigned boundaries, inconsistent
stored type bits, opaque fill/type bytes, aliases/gaps/reversed pointer order,
absent/empty/repeated blocks, strict late input refusal without writing/reporting,
standalone/bundle equality, repeat output and immutable bundle refusal.

## Conditional quick-backdrop rectangle inputs

Each placement candidate adds nullable `conditional_quick_rectangle_inputs`.
Only a live quick-backdrop definition (type 0) receives this annotation. Ordinary,
non-backdrop and deleted definitions have null; missing definitions remain absent.
Every ambiguous quick candidate has its own rectangle inputs. No incoming record
creation type, application-global definition or another frame selects a winner.
The context-free header/placement decoders retain their existing contracts.

The annotation contains `fields.x/y/width/height`, with `record_offset`, raw u16
and signed i16 values read from the candidate's conditional refreshed record.
X/Y are at 2/4 (untouched by refresh); width/height are at 26/28 (copied from the
supplied local header's 34/36). It exports the original renderer's two rules:

- Origin = signed record coordinate minus signed runtime translation word.
- Exclusive endpoint = origin plus signed refreshed dimension word.

`translation_inputs.x/y` identifies the two runtime word addresses, 0x41d662 /
0x41d664, with `signed_i16: null`. Their live values, initialization and meaning
are unavailable here; the export does not call them a camera or scroll position.
`zero_translation_edges` gives left/top/right_exclusive/bottom_exclusive only
under the explicit hypothetical assumption both runtime translation words are
zero. It never normalizes, clamps, rejects or substitutes zero/negative dimensions,
never wraps endpoints back to 16 bits, and never assigns a stored sentinel meaning.
The signed word arithmetic fits int32 even at the extreme differences/endpoints.
This is an exclusive arithmetic rectangle, before culling, clipping or drawing;
it does not prove a pixel was drawn or describe the inclusive fill clip path.

`meaning` is `conditional_quick_rectangle_inputs`, `evidence` is
`original_runtime_origin_subtraction_and_quick_rectangle_paths`, and
`runtime_resolution` is false. `coverage.conditional_quick_rectangle_inputs`
is true; arena geometry, runtime rendering, globals, spawns and behavior remain
false. These are conditional drawing inputs, not effective arena bounds: header
selection, record mutation until rendering, translation state, render gates,
collision and spawns remain unresolved. Previous artwork, records and refresh
annotations remain byte-for-byte unchanged. The bundle component schema follows version 7.

Independent source-span traversal verifies every one of the original's 69 quick
placement candidates; other candidate types retain null. Local Unicorn 2.1.4
executes the unmodified complete refresh helper 0x40f250 and two separate renderer
instruction paths: origin subtraction 0x4057db..0x405804, and quick exclusive
endpoints 0x405886..0x4058c8. Actual origin outputs are passed unchanged to the
endpoint path. This is not execution of the intervening renderer gates or a full
renderer call. Supplied runtime words, records and headers are DATA; no instruction,
import or callback is replaced. All 69 source candidates run seven asymmetric
translation pairs, plus 343 signed-boundary and 512 seeded contexts and one wrong
unsigned expectation (which fails): 1,339 contexts / 4,017 path executions.
Every refreshed byte, source header, stack, preserved registers and instruction
span is checked. Source/project/executable bytes remain unchanged and private.

Eight tests cover signed boundaries, asymmetry, zero/negative dimensions, opaque
neighbors, old record fields differing from headers, all fill kinds, ambiguous
local/global-flagged headers, ordinary/deleted/missing scope, alias/reversed/gapped
slot pointers, absent/empty/repeated placement blocks, bundle/standalone equality,
immutable refusal/repeats, original absolute spans and late invalid headers before
any output or optional fault report. Existing detached optional private fault
reporting is unchanged; no translation state, original content or endpoint enters
reports. Original executable proof and generated exports remain ignored/private.

## Conditional quick-backdrop fill call inputs

Schema 7 adds nullable `conditional_quick_fill_inputs` to the same live quick
placement candidates as rectangle inputs. Ordinary/deleted/non-backdrop candidates
are null; missing definitions remain absent. Every ambiguous local/global-flagged
quick header has its own annotation, with no application-global fallback or winner.
The annotation consumes the conditional refreshed record, not its old fill/image/
color words. Existing source bytes, artwork, refresh and rectangle fields are unchanged.

`fill_word` retains the complete u16 at record +24, its offset and dispatch low
nibble. `image_word` retains u16 at +8; `colors` retains the complete dwords at
+16/+20, including high bytes without inventing alpha/import color semantics.
The original fill path dispatches on `fill_word & 0x000F`:

- 0: `branch: solid`, with `solid_color_raw_u32` from +16.
- 1 with zero image word: also `branch: solid`, with explicit
  `mosaic_zero_image_solid_fallback: true` and the same +16 color input.
- 1 with any nonzero image word, including 0xFFFF: `mosaic_metadata_required`.
  Actual lookup, tile dimensions/loops and pixels are unresolved.
- 2: `branch: gradient`, with `gradient_arguments`. Bit 0x0100 swaps the two
  raw color arguments. It is independent of low-byte orientation bit 0x0010.
  `flags_raw_u16` is `fill_word & 0x00F0`; it is not a full dword call argument.

The original uses `mov dx` and `and dx`, then **pushes edx**. Incoming EDX's high
16 bits survive into the gradient flag argument. `flags_high_u16_input` therefore
stays null; `flags_argument_rule` retains the incoming-high-word rule. No zero
extension, meaning for those upper bits, or import interpretation is guessed.
The editor artwork view continues to describe the header's low byte; the new
runtime call view establishes one high-byte bit without reinterpreting other bits.
Existing strict header artwork validation and image-bank membership are unchanged:
a synthetic mosaic-zero header still needs slot 0 for that earlier editor view.
Direct `quick_fill_inputs` requires exactly 32 record bytes and refuses unsupported
low nibbles; context-free header and placement decoders retain their contracts.

`clipping_inputs` lists supplied signed-int32 origin X/Y and right/bottom clip
arguments with null values. The original prologue computes signed minimum of
`origin + signed_refreshed_dimension - 1` and supplied clip for each endpoint.
Arithmetic wraps to 32 bits before the signed comparison. No left/top clamp,
positive-size requirement, empty-rectangle rejection or normalization is invented.
Unlike the existing exclusive rectangle preview, this is an inclusive call-input
rule. The annotation does not calculate unknown live endpoints. Caller culling,
translation selection and all fill/metadata imports remain unresolved.

`meaning` is `conditional_quick_fill_call_inputs`, `evidence` is
`original_runtime_fill_dispatch_and_call_argument_paths`, `runtime_resolution`
and `drawing_performed` are false. `coverage.conditional_quick_fill_inputs` is
true; rendering, arena geometry, global resolution, spawns and behavior remain
false. This supplies a later renderer/spec with proven inputs, not a drawn arena.
The immutable research bundle records component schema 7; move a different old
bundle aside before regeneration. Invalid input still exits 2 before either
output/reporting; existing detached optional private fault reporting is unchanged.

Evidence uses the unchanged original executable hash above. Independent local
Unicorn 2.1.4 executes complete refresh helper 0x40f250 and the original fill
function prologue/dispatch/argument assembly from 0x4054b0 to the **first call**:
0x4055d9 (solid), 0x4055b6 (gradient), or 0x405528 (mosaic metadata). It stops before
executing the call instruction; there are no patched instructions/imports/callbacks.
These are conditional fill-entry executions after refresh, not actual loader or
renderer caller execution. Every refreshed byte, unchanged header, original
instruction span, saved callee registers, entry stack and assembled call argument
is checked. Gradient tests vary incoming EDX high bits and show a wrong
zero-extended flag expectation fails on actual pushed 0xDEAD0010.

4,411 supplied contexts / 8,822 original path executions cover every high fill
byte with six low fills and zero/nonzero image handles (3,072), asymmetric signed
word/int32/wrapping/clipping boundaries (343), seeded random int32 contexts (512),
all 69 original candidates with seven contexts each (483), and the incorrect
flag expectation (1). Independent absolute project-byte spans check all original
candidates: 24 gradient / 45 mosaic, all stored high fill bytes zero. Solid,
zero-handle fallback and high-byte color swaps are synthetic capabilities, never
claimed as observed original gameplay. Eight new tests also cover other candidate
types, ambiguity, opaque neighbors, alias/reversed/gapped slots, absent/empty/
repeated blocks, strict late malformed refusal, bundle/standalone equality and
immutable repeats. No original assets, instructions, proof data or exports are committed.
