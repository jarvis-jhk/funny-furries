# Backdrop artwork and refresh inputs and dimension candidates v4

`tools/backdrop_dump.py` exports the artwork fields stored directly in ordinary
and quick-backdrop definition headers. It supplies image handles and editor fill
colors for a later arena decoder. Version 4 adds complete ordered placement-refresh inputs alongside the
ordinary-image candidates and quick-backdrop dimension inputs. It does not render
an arena or establish final placement coordinates, shape, collision, spawns or
runtime behavior. Effective ordinary-backdrop runtime dimensions remain unresolved.

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

- `schema_version` is 4 and `exporter` is `backdrop-dump/4`. All previous raw
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
