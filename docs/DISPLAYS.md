# Display artwork storage v1

`tools/display_dump.py` exports the score/lives/counter data blocks as ignored
`export/<source-sha256>/displays.json`. It completes another object-to-image
storage prerequisite for M0. It does not define how scores, lives or counters
are rendered, assigned to players, updated by events or resolved globally.

```
python3 tools/display_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Requirements, private output policy and optional detached `FF_FAULT_REPORT_URL`
handling match [EXPORTER.md](EXPORTER.md). Input validates completely before
atomic replacement. Symlinks are refused; write failures leave existing output
intact and remove temporary files. Exit 0 means success, 2 invalid input, 1 an
unexpected implementation/write fault. Fault delivery contains only the exporter
version, platform and exception class. Original bytes, paths and exception text
never enter it. No private endpoint is embedded.

## Contract

- Source and reader fingerprints match the project index. All global and local
  definition lists and their slots are retained, including deleted/other types,
  empty/missing lists and reference-only global-flagged local definitions.
  Those slots have an empty `display_data`, without inventing resolved content.
- Every type 5/6/7 data block (nested kind 0) retains its original block index,
  offset relative to its definition list, full `raw_hex`, size and SHA-256.
  Missing data differs from a present malformed/empty block, which is rejected.
- The supported CnC payload has a 46-byte prefix ending in `SCRE`, `LIVE` or
  `CNTR` at byte 42, according to the object's type. `prefix_hex` is unaltered.
- Counters have a length-prefixed attribute region at byte 46. Its u16 length
  includes that length word and must be at least two bytes and in bounds.
  `counter_attributes` retains its offset, length and complete raw bytes;
  initial/minimum/maximum values and other fields are not interpreted.
  For score/lives objects it is null.
- After the prefix/attributes, sections are contiguous through payload end.
  Each starts with u16 byte length and u16 raw type, and retains its storage ID,
  offset, byte length and complete `raw_hex`. Lengths include the header and
  must be at least four bytes and in bounds. No tail is silently discarded.
- Only section types 1 and 4 are interpreted as image lists: an 8-byte header
  with u16 count at +6, followed by that many ordered u16 image-bank handles
  at +8. The section must contain exactly `8 + 2 * count` bytes. Header words
  at +4 and the runtime meanings of list positions/type numbers stay unknown.
  Repeated handles retain their order; zero handles is an empty list.
- Every decoded image must be occupied in at least one retained image bank.
  `image_bank_candidates` is parallel to `image_ids`, with all matching bank
  segment IDs for each handle. Repeated banks retain their identities; no
  runtime bank selection is guessed.
- All other section types are opaque, including the original types 0 and 3.
  `image_ids` and `image_bank_candidates` are null. Their bytes are preserved
  even if they resemble unoccupied image handles. This is distinct from an
  interpreted empty list. Unknown modes cannot be used for runtime rendering.
- Prefix + counter attributes (if present) + ordered section bytes reconstruct
  every payload exactly. Raw bytes, offsets and hashes remain authoritative.
  `coverage.runtime_display_semantics`, `global_reference_resolution`,
  `other_object_images` and `behaviour` are false.

## Evidence and limits

Pinned KlikBack `icon_census.display_first_frame` independently establishes
object signatures, the counter attribute extent, first-section length/type and
first image at +8; for counters it explicitly recognises modes 1 and 4. It is
an editor-icon helper, not evidence for complete runtime numeric rendering.

The counted list shape, complete section extents and contiguous traversal were
inferred from and checked against every local original payload. All 27 payloads
(4 score, 2 lives, 21 counter) reconstruct exactly. Their 33 sections consist of:
8 score type-1 lists, 2 lives type-4 lists plus 2 lives type-1 lists, 6 counter
type-1 lists, 13 opaque counter type-0 sections and 2 opaque counter type-3
sections. All 178 interpreted image references match independent source-word
reads; first-section images agree with the external icon helper. There are 110
reference-only definitions with no data, retained without resolving them.

This supports the observed CnC dialect, not every Clickteam format. Counter
mode-4 lists, zero-length lists, unknown types and changed list order have
synthetic storage evidence only. Digit-to-image meaning, signs/separators,
player ownership, bar/text rendering, numeric attributes, global resolution,
font/text/extension artwork and behaviour remain separate work.

Tests run on Python 3.10+, with `FF_KLIKBACK_SRC` for synthetic containers and
optional `FF_TEST_PROJECT` for all original data. Synthetic projects exercise
known list order/repeats, multiple sections, opaque words, attributes, empty
lists, globals/deleted/reference-only slots, missing/empty lists, bank gaps and
repeated banks. Bad signatures/lengths/counts/tails, unoccupied handles, late
invalid data before output, atomic write failures, symlinks and fault
classification are covered. No original artwork or metadata is committed.
