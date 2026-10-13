# Local image export v1

`python3 tools/image_dump.py /local/FF2xmas.decompiled.cca --klikback-src /local/KlikBack/src`

Uses the externally supplied CnC container reader described in EXPORTER.md.
No Pillow or other runtime dependency is needed. Original graphics and generated
metadata belong only in ignored `export/<source-sha256>/images-v1/`. Never commit,
publish or release them. This is a local asset exporter, not a playable engine.

## Supported records and evidence

This decoder handles only mode 4 (24-bit BGR), flags 0x40 (TGF rows, raw colours)
or 0x44 (TGF rows, RLE colours). Every one of the local original's 614 bank images
uses these forms: 10 raw, 604 compressed. Other pixel modes and flag combinations
fail explicitly; no palette, colour-key or alpha-channel rules are guessed.

The 24-byte record header stores checksum/references at offsets 0/2, payload size
at 6, width/height at 10/12, mode/flags at 14/15, and unsigned 16-bit hotspot/action
coordinates at 16..23. Coordinates are retained as raw u16 values; signed coordinate
interpretation and runtime anchor/animation use are outside this slice. The header
and full-record hash are retained for provenance.

Payload begins with a u32 decoded buffer size, followed by height pairs of u32
opacity/colour pointers. Pointers are relative to the byte after the buffer-size
field. Opacity bytes are (transparent-count, opaque-count) pairs per row; trailing
unrepresented row pixels are transparent. Colour pointer differences must match
exactly three bytes per opaque pixel. Explicit opacity determines transparency:
an opaque black pixel remains opaque, transparent pixels export RGBA (0,0,0,0).
BGR colour bytes become RGB with alpha255 without quantization or scaling.

Compressed colours use a one-byte count: high bit = literal, otherwise repeat
one BGR triple; lower seven bits = pixel count. A final zero terminates the stream.
Zero-length literal runs, overruns, excess/missing decoded colours, trailing bytes
and missing terminators fail. Raw buffers contain exactly the declared colours,
then zero padding aligning the *whole decoded buffer* to four bytes. All six
padded raw records in the local original satisfy that rule. Zero dimensions and
images above 4,194,304 pixels fail before allocating a pixel buffer.

The image decoder is implemented here, independently of KlikBack's image module.
Original-file tests compare every PNG pixel/alpha against the pinned external
`tgf.image.parse_record`/`decode_rows`, and read bank offsets/sizes directly from
the source slot table. Handwritten synthetic colour/transparency and literal/repeat
fixtures additionally establish expected channel order and alpha explicitly.
The oracle agreement establishes stored pixel extraction, not original gameplay
rendering, sprite selection, timings, palette effects or runtime colour-key rules.

## Bundle and failure contract

Manifest schema1 records exporter/source/reader fingerprints and ordered banks,
segment positions, original slot IDs/offsets/sizes, raw headers, record/PNG/RGBA
hashes, dimensions, mode/flags and raw hotspot/action coordinates. Gaps never get
compacted. Repeated banks use distinct segment positions; absent and empty banks
remain distinct. Files are `image-<segment-position>-<slot>.png` plus manifest.json.
PNG uses RGBA8, filter0, zlib IDAT, CRC-protected chunks and no interlacing.
Transparent pixels carry zero RGB; compressed source bytes are not preserved in
PNG, while decoded opaque colour bytes are preserved exactly. PNG compressed
bytes are reproducible in the same zlib environment, not promised identical
across zlib versions. RGBA hashes remain independent of PNG compression.

All source records validate before writing. A sibling staging directory holds the
complete bundle; rename installs it once. Write/rename failure removes staging.
A repeat run verifies every filename and byte, refusing missing/extra/changed files,
non-directory destinations and symlinks without replacing an existing bundle.
Cross-zlib byte differences likewise require moving the existing bundle aside.

Malformed/unsupported input and changed output exit2 without sending a report.
Unexpected or output-write faults exit1 and use the detached optional private
`FF_FAULT_REPORT_URL` reporter with image-dump version/platform/exception class;
paths, original content and exception messages never leave the process. No endpoint
is embedded. This is not a game crash relay or a Windows/Deck operation claim.

Still required for M0: global event container/semantics, opcode/parameter meanings,
object-to-image animation mapping, arena JSON and observation-backed behaviour.
