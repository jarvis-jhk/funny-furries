# Combined research export v1

Run every supported M0 research exporter against the same local project:

```
python3 tools/export_project.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Python 3.10+ and the separately supplied reader pinned in [EXPORTER.md](EXPORTER.md)
are required. No original content or reader implementation is bundled here.
Output is the ignored `export/<source-sha256>/research-v1/` directory. It contains
original assets and metadata; never commit, publish or release it. This command
does not modify the original or the individual exporters' existing outputs.

## Contents and contract

The flat bundle contains `project-index.json`, `events.json`, `events.txt`,
`frame-layout.json`, `animations.json`, `backdrops.json`, `displays.json`,
`audio-manifest.json`, `image-manifest.json`, all supported WAV/MIDI/PNG files,
and its own `manifest.json`. Media filenames and bank/segment/slot identities
are unchanged. File names in the audio/image manifests resolve inside this
same directory; their former `manifest.json` names become distinct component
manifest names. Component schemas and versions are recorded from the current standalone tools;
event schema4 includes editor group structure. Older snapshots must be moved
aside explicitly before exporting changed component bytes.

The top-level schema1 manifest records source/reader fingerprints, component
schema/exporter versions, and a sorted list of every other file's byte count
and SHA-256. It excludes itself from that list to avoid a circular hash.
Its coverage explicitly leaves arena geometry, spawns, event semantics,
behaviour and a playable runtime false. The `supported_research_exports` flag
means only that the listed existing tools completed; it is not M0 completion.
Absent/empty/repeated banks and frame programs retain their existing contracts.

Input bytes are read once. All components decode and validate before output
creation, including agreement on source and reader fingerprints. A malformed
or unsupported late component prevents the whole bundle from being written.
There is no per-component partial-success mode.

Files are staged in a sibling temporary directory, then a single rename makes
the complete bundle visible. Failed writes/rename clean staging and leave no
partial bundle. Repeated runs verify every filename and byte of an existing
bundle without changing it. Missing, additional, modified or symlinked files,
directory replacements and symlinked output roots are refused. Bundle files
have flat, validated names and the source directory uses a validated SHA-256.
Move an old bundle aside explicitly when a changed exporter or zlib version
produces different bytes; retries do not silently repair or replace it.

Exit codes are 0 success, 2 invalid/unsupported input or conflicting existing
output, 1 unexpected implementation/write fault. The optional detached
`FF_FAULT_REPORT_URL` reporter identifies `export-project/1` and sends only
platform/version and exception class, never source paths/data/exception text.
There is no private endpoint in source. Normal input failures are not reported.

## Evidence and limits

Integration tests use entirely synthetic objects, frame/global events,
placements, image/audio banks with gaps, and repeated/empty banks. Independent
WAV/PNG readback and lossless event/placement reconstruction check that composing
the tools keeps their output intact. Late invalid images, mismatched component
fingerprints, changed existing trees, unsafe paths, write/rename failures and
fault classification are exercised. CI runs these on the pinned reader without
original game data. The optional local-original test installs and reads back
the full bundle (614 PNGs, 17 WAVs, 2 MIDI files).

This combines existing structural exports into one usable research snapshot.
Opcode/parameter meanings, placement fields/arena geometry/spawns, global
runtime resolution and observation-backed gameplay rules remain open. There
is no arena JSON decoder or engine loading this bundle yet; this command alone
does not finish the combined exporter/spec roadmap item.
