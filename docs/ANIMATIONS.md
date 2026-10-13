# Active animation storage v1

`tools/animation_dump.py` maps stored active-object animation slots and directions
onto numeric image-bank handles. This bounded M0 slice supplies image sequences,
not movement, playback timing, animation transitions or a behaviour specification.

Use Python 3.10+ and the externally supplied reader described in [EXPORTER.md](EXPORTER.md):

```
python3 tools/animation_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Output is ignored `export/<source-sha256>/animations.json`. It contains original
object data, so never commit, publish or release it. The input is read once and
never modified. Complete container/animation/image-handle validation precedes
atomic replacement. Repeat exports with identical source/reader bytes are
byte-identical. Failed writes preserve the previous file and clean temporary
files; output symlinks are refused. Exit codes are 0 success, 2 invalid or
unsupported input, 1 unexpected/write fault. Unexpected faults use the existing
detached optional private `FF_FAULT_REPORT_URL` reporter, with only exporter
version/platform/exception class. No endpoint, path or original data is reported.

## Contract

- Source and reader fingerprints match the project index.
- Ordered global-definition lists retain their segment index/offset; each frame
  retains ordered definition blocks with block index/offset. Every object slot,
  numeric type and global/deleted status remains present. Global local references
  without data remain empty: this exporter does not resolve them by name or index.
- Only active type 2 object-data blocks are decoded. Repeated blocks retain their
  indices and object-list offsets. Non-active data/icons remain outside this
  export; missing active data remains distinct from a decoded empty animation set.
- Each decoded block retains its complete `raw_hex`, length and SHA-256. Every
  offset below is relative to that object-data payload, not the object record,
  list, frame or file. Prefix, tail and unparsed animation gaps also remain raw.
- The supported dialect has `SPRI` at offset 42. The u16 at 46 gives sprite-block
  length measured from 46, including that word; the animation base follows it.
  The animation header is four bytes: its first u16 is region byte length,
  including header/tables; the second word remains opaque.
- A table of 16 u16 pointers follows the header. Each is relative to animation
  base; values >= 0x8000 are absent, with the exact value retained. A present
  animation addresses 32 u16 direction pointers relative to its own table.
- A present direction addresses an eight-byte header. Its first six bytes remain
  opaque; u16 at +6 counts following u16 image handles, in stored order including
  repeats. Zero frames, absent direction and absent animation remain distinct.
- All slots retain their IDs, raw pointers and nullable offsets/contents. Exact
  same-kind record aliases are allowed without compacting slots. Partial overlaps,
  incompatible record aliases, pointers into headers/tables, truncated headers,
  invalid lengths and out-of-region frame arrays are refused.
- Unreferenced region bytes are explicitly listed as opaque spans. They are not
  discarded or guessed to be animation names. Animation length bounds the decode;
  trailing object bytes are retained, without assigning meaning.
- Image banks retain ordered segment IDs/offsets and occupied handles. Every
  decoded handle must exist in at least one bank. Repeated banks stay separate;
  validation does not select a runtime bank or resolve ambiguity. The IDs can be
  compared with [IMAGES.md](IMAGES.md)'s numeric PNG slots.
- `coverage` distinguishes implemented storage/handles from runtime semantics,
  global reference resolution, other object images and behaviour (all false).

## Evidence and limits

Pinned KlikBack `6e178b9470206f71871417dec852fbfa24cd01b9` supplies independent
structural evidence in `tgf/icon_census.py::sprite_first_frame` and
`tgf/unprotect.py::_active_animation_end`: SPRI/sprite extent, 16 animations,
32 directions, relative pointer bases, absent values, +6 count and +8 handles.
Our decoder is independently implemented; only the external container reader
is imported at runtime. Neither those helpers nor this slice establish animation
names, direction angles, speed, looping, event selection or runtime fallbacks.

Every local original active payload satisfies the declared animation length,
with opaque gaps and an 80-byte opaque tail. Local verification covers 83 stored
active payloads, 131 present animations, 256 present directions and 940 image
references; 815 frame-local active definitions have no data. All complete active
payloads are retained byte-for-byte. The original test independently reads each
pointer/count/image word directly from source bytes and compares the first image
with KlikBack's icon helper. Synthetic fixtures cover aliases, absent slots,
repeated images/banks, raw unknown headers/gaps/tails, global definitions,
reference-only/deleted slots and zero-frame/empty sets. CI requires the pinned
reader but explicitly skips the local-original fixture unless supplied.

Full M0 still needs other object artwork, global reference and event decoding,
placement/arena geometry/spawns and observation-backed behaviour. Exported numeric
image sequences do not establish original gameplay or Windows/Deck operation.
