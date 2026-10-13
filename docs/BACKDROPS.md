# Backdrop header artwork v1

`tools/backdrop_dump.py` exports the artwork fields stored directly in ordinary
and quick-backdrop definition headers. It supplies image handles and editor fill
colors for a later arena decoder. It does not render an arena or establish
placement coordinates, dimensions, shape, collision, spawns or runtime behavior.

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
- `coverage` distinguishes header artwork/image handles from runtime rendering,
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
