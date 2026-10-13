# Audio export v1

This M0 slice exports the **observed unprotected CnC audio-record dialect**
from a player's local copy. It supports PCM samples as WAV and Standard MIDI
Files without transcoding. It is not a player, image exporter or behaviour spec.
Use Python 3.10+ and the separately supplied pinned KlikBack reader described
in [EXPORTER.md](EXPORTER.md):

```
python3 tools/audio_dump.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

Output is an ignored `export/<source-sha256>/audio-v1/` bundle: `manifest.json`
and `sound-<segment-position>-<slot>.wav` / `music-<segment-position>-<slot>.mid`.
**All output contains original game content. Never commit, publish or release it.**
Filenames use numeric identities, never original names or paths. Bank slots stay
uncompacted; repeated banks remain distinct, absent banks stay absent and present
empty banks stay present. Names/unknown header fields survive only in the
manifest's raw header. No event-to-audio mapping or runtime handle interpretation
is inferred.

## Input and output contract

The index's strict container/object/bank validation runs before audio decoding.
Each occupied audio entry has a 32-byte preserved header. The little-endian
length at offset 6 must equal the bytes after that header. The word at offset
30 is 1 for the supported sound records, 2 for music. These offsets were
established by inspecting **every** entry in the local FF2 Xmas decompiled
project; they are not a claim about other Clickteam versions. Unknown header
fields stay opaque. The external reader supplies bank boundaries, not audio
decoding.

Sound records carry a 16-byte PCM format at offset 32, then samples at offset
48. Only format 1, mono/stereo, 8/16-bit PCM is supported. Sample rate must be
positive; byte rate and block alignment must agree with channel count/bit depth;
sample bytes must form complete interleaved frames. Samples stay byte-identical
(8-bit unsigned / 16-bit little-endian); the tool adds a RIFF/WAVE wrapper with
`fmt ` and `data` chunks. Odd sample-byte lengths receive one zero pad byte
**outside** the data chunk's declared length. No normalization/resampling occurs.

Music bytes after offset 32 are copied unchanged. SMF header length 6, formats
0/1/2, positive track count, format-0 single-track constraint, positive
ticks-per-quarter division, each `MTrk` length and exact file consumption are
checked. SMPTE timing, alternate header sizes and non-track chunks are refused.
MIDI events, running status, instruments, playback and synthesis are **not**
validated by this exporter; `midi_event_semantics` remains false. Independent
parsing of the local original is additional evidence, not a broader guarantee.

Manifest schema 1 records exporter/source/reader fingerprints and ordered banks
with their segment position, numeric kind and ordered occupied slots. Entries
record original bank-relative offset/length, header hex, record SHA-256,
relative output filename/length/SHA-256 and decoded PCM or MIDI container fields.
PCM entries also record the sample-frame count and sample SHA-256. No timestamps
or machine paths enter output. The project index's inventory coverage does not
change; the audio manifest claims only its supported audio-file conversion.

Every record is validated before writing starts. A sibling temporary directory
holds the complete bundle, which is renamed into place once. Failed writes or
rename leave no partial bundle; staging is cleaned. Repeat runs verify every
filename and byte in the installed bundle. A changed, incomplete or additional
file causes refusal; move the old bundle aside explicitly before regenerating.
Existing bundles are never overwritten. Symlink output directories/files are
refused. JSON and audio bytes are deterministic for identical input/reader.

Exit codes: 0 success, 2 malformed/unsupported input or refused destination,
1 unexpected/write fault. Unexpected faults use the existing detached optional
`FF_FAULT_REPORT_URL` reporter, with audio exporter version/platform and exception
class only. No original data/path/message or endpoint is committed or transmitted.

## Verification and limits

Synthetic tests use only authored fixtures: mono/stereo, 8/16-bit and odd-length
PCM, MIDI chunks, missing/repeated banks, gapped slots, malformed formats/counts,
atomic bundle failures, repeat verification, symlinks and fault classification.
Python's separate `wave` reader checks headers, frame counts and exact samples.
The optional original test reads slot offsets directly from the source bank table
and verifies every extracted sample/MIDI byte, format and manifest fingerprint.
Use `FF_KLIKBACK_SRC` and local-only `FF_TEST_PROJECT` as in EXPORTER.md.

The local original contains 17 sounds at slots 0–9, 11–14, 16–18, and two music
records at slots 0/1. Independent Mido 1.3.3 parsing confirms the MIDI containers
and event streams; original MIDI bytes remain unchanged. Mido is a local evidence
tool, not an exporter or CI dependency. This proves conversion of this source,
not original playback timing, instrument sound, Windows/Deck operation or a
complete asset exporter. Global/event semantics, images, arenas and an
observation-backed behaviour specification still remain in M0.
