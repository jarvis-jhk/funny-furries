# Notes

2026-10-13: repo and lane created (JARVIS adhoc, t_mv5tuz6swmao5). Nothing implemented yet.

2026-10-13: Sol tick t_mv69hxqvbzzg5, first bounded M0 slice: project index v1
(`tools/project_index.py`, contract `docs/EXPORTER.md`). Clean main checkout,
origin fetched, no open issues/PRs or in-flight work at start. Direct main commit
for this new repo; no other branch/commit policy is defined in the brief.

The exporter uses a separately supplied KlikBack reader, tested at commit
6e178b9470206f71871417dec852fbfa24cd01b9. Index preserves original frame/object
slots, deleted/global flags, container/block offsets and occupied asset-bank IDs.
It records source and reader fingerprints, explicitly marks event semantics,
media files and arena geometry unsupported, and writes only ignored export/.
Input validation precedes atomic replacement; corrupt containers and inconsistent
tables fail, symlink destinations are refused. Unexpected/export-write faults
have detached optional private reporting through FF_FAULT_REPORT_URL; payload
contains only version/platform/exception class. Tests mock delivery, no live
report posted and no private endpoint in source.

Validation: Python compileall passed; 10 unittest cases passed with the external
reader and local original enabled, including synthetic slot gaps/deleted/global
objects, truncation/bad addresses/count/bank lengths, deterministic atomic writes,
symlink refusal and fault classification/delivery. Local original SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0:
13 frames, 133 global definitions, per-frame definitions 0/3/111 then ten*137;
banks image614/music2/sound17. Original bytes unchanged, repeat JSON byte-identical.
CLI exercised on the original; generated metadata and original data stay untracked.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. CI workflow
uses Python3.10 and the pinned external reader, never original game content.
Local evidence: data/furries/project-index/ in the agent state volume.

M0/combined furries-exporter-spec remains started by sol: this is only inventory.
Next bounded slice should decode readable ordered events with parameters and
explicit unknown-opcode evidence; media extraction, arena JSON and observation-
backed behaviour spec also remain. No engine, playable build, release, hardware
claim, new schedule or CI continuation. Native Windows/Deck exporter operation
is not established by this Linux run.

Delivery: source commit 7b64c5979364bd7e009b4f60762175ad05e2d423 pushed to main.
Exporter tests CI38354022066 completed successfully on that exact commit:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38354022066 . Downloaded
job115152630746 log confirms actual checkout SHA, pinned reader SHA and Python3.10
execution: 10 cases, 9 pass, only the local-original case explicitly skipped.
All10 ran locally with the original enabled. ci.json and ci-job.log saved with
local evidence. This follow-up changes NOTES only; tested source unchanged.

2026-10-13: Sol tick t_mv69txhy0juws, bounded M0 event-structure v1 slice.
Clean main, fetched origin, no open PRs/issues or in-flight continuation at start.
Direct main follows the initial repository convention. `tools/event_dump.py`
exports ordered frame rows/conditions/actions and typed raw parameter payloads
as JSON or readable text; `docs/EVENTS.md` specifies offsets and limits.
All opcode/parameter meanings remain unknown, references remain numeric,
global-event segments and auxiliary editor blocks remain opaque. No behaviour
or playable-engine claim. Unexpected faults use the index's detached optional
private reporter with the event exporter's own version/title; no endpoint is
committed. Ordinary malformed input is not reported.

Strict Fra v0217 header, signed row lengths, counts, record/parameter sizes,
terminators and exact byte consumption are checked before an atomic single-file
write. Missing frame events stay distinct from empty programs. The shared
writer preserves index output unchanged and rejects symlink destinations.
Generated events.json/events.txt contain original data and stay ignored.

Local validation: compileall and all18 unittest cases pass with the pinned
external reader and original enabled. Original SHA-256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
All13 frames, 1186 rows (0/4/52 then ten*113), 2490 conditions, 5083 actions
and6685 parameters checked; every complete frame event block and the opaque
global payload reconstruct byte-for-byte. Both CLI formats exercised twice,
repeat files byte-identical, input unchanged. An executed negative control
omitting the first parameter payload byte fails three intended reconstruction
tests; source restored before the final positive run. Malformed sizes/counts,
unknown codes, signed references, empty/absent programs, truncation, terminator
tails, failed atomic writes, symlinks and fault classification are covered.
Evidence: agent state data/furries/event-dump/ (positive/negative logs and
fingerprints); no original content is committed there or published.
Actual agent TypeScript compiler passed after restoring locked dependencies
with `npm ci --include=dev --ignore-scripts`; no agent source/lockfile changed.

Combined furries-exporter-spec stays started/sol. Next bounded slice can decode
the global-event container or establish opcode/parameter semantics against
independent evidence. Media files, arena JSON and observation-backed behaviour
spec remain. No new schedule, release, hardware claim or second slice.

Delivery: tested source 9fa50502cb7f6c4004709aa67efdb0259446a0ad pushed main.
Exact-source CI38355190154 completed/success:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38355190154 . Downloaded
job115156318783 log verifies actual checkout SHA and pinned reader SHA, Python3.10
compileall and all18 cases (16 pass, only the two original-file fixtures skipped).
All18 passed locally with the original enabled. Current evidence and CI logs:
data/furries/event-dump/. No in-flight work or CI continuation remains; this
delivery update changes NOTES only and preserves the tested source.

2026-10-13: Sol tick t_mv6axhx46z8qm, bounded M0 audio-export v1 slice.
Clean main/fetched origin, no open PRs/issues or in-flight work at start; direct
main follows the initial repository convention. `tools/audio_dump.py` and
`docs/AUDIO.md` export local supported CnC audio records as an ignored immutable
`audio-v1` bundle with a manifest, numeric bank/slot filenames and fingerprints.
17 PCM samples become WAV without changing any sample byte; both MIDI records
are copied unchanged. Slots 10/15 stay absent; repeated banks retain separate
segment positions, missing and empty banks remain distinct. Original record
header bytes stay opaque in the manifest; runtime/event mappings are unknown.
Audio dialect offsets are observation-backed against every local original
entry, not borrowed from a different Clickteam version. MIDI container lengths
are checked, but event semantics/playback/synthesis are outside this exporter.

All records validate before output starts. A complete sibling staging directory
is renamed into place once; failed writes/rename clean staging and leave no
partial bundle. Repeat exports verify every file/byte; changed/incomplete/extra
files and symlinks are refused without replacing the existing bundle. Malformed
input is exit2 without reporting; real unexpected/write faults are exit1 through
the existing detached FF_FAULT_REPORT_URL reporter, carrying only version/platform
and exception class. No endpoint or original content is committed or published.

Validation: compileall and all26 unittest cases pass locally with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Direct source-bank
slot table reads and Python wave readback prove exact PCM/MIDI extraction and
correct mono/stereo 8/16-bit headers, interleaving, sample counts and odd-length
RIFF padding. Synthetic invalid formats/rates/alignment, bad MIDI lengths/counts,
gapped/repeated/empty banks, late invalid entries before save, symlinks, atomic
write/rename failures and fault classification run. An executed negative control
reversing PCM sample bytes fails four intended assertions (original extraction
plus all three synthetic PCM shapes); source restored byte-exact before positives.
Both CLI runs succeed and verify the identical 20-file bundle. Original SHA-256
remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0,
input unchanged. Independent ffprobe reads all17 WAV formats; Mido1.3.3 parses
both original-byte MIDI files (format0/one track/96PPQN/3659 events and format1/
21 tracks/120PPQN/8110 events, all tracks terminate). Mido/packaging are data-only
local evidence dependencies, not repo/CI/runtime dependencies. Actual agent
./node_modules/.bin/tsc --noEmit passed before commit. Evidence:
agent state data/furries/audio-dump/; generated assets remain ignored/private.

Combined furries-exporter-spec stays started/sol. Global containers/opcode and
parameter semantics, images, arena JSON and an observation-backed behaviour
spec remain. Initial global-container research found the newer reader's
KLBEDAEH format does not match this CnC source; no guessed decoder was committed.
No engine, release, Windows/Deck/hardware claim, new schedule or second slice.

Delivery: source ef3b76ccf6bad4d6a6a0fb4fe6dd90ed51ba9dde pushed to main;
Exporter tests CI38357851622 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38357851622 . Downloaded
job115164807756 log confirms actual checkout SHA, pinned reader SHA, Python3.10
compileall and all26 cases (23 pass; only three local-original fixtures skipped).
All26 passed locally with the original. CI snapshot/logs saved alongside local
evidence in data/furries/audio-dump/. No in-flight work or CI continuation.
This final delivery update changes NOTES only; tested source unchanged.

2026-10-13: Sol tick t_mv6bmy5hanxg7, bounded M0 image-export v1 slice.
Clean main/fetched origin, no open issues/PRs or in-flight continuation at start;
direct main follows the existing convention. `tools/image_dump.py` and
`docs/IMAGES.md` export local mode4 TGF truecolour banks as RGBA PNG, with ordered
bank/segment/slot IDs, raw header/anchor values and record/PNG/RGBA fingerprints.
All614 original images supported (10 raw/604 RLE); no graphics or generated
metadata committed/published. Gaps/repeated/empty/missing banks remain distinct.
Original image decoder implemented here; no external image code copied. Other
modes/flags fail explicitly, runtime colour-key/animation semantics stay unknown.

Strict record size, dimensions/pixel cap, monotonic row pointers, opacity/colour
counts, bounded literal/repeat RLE, final terminator and exact byte consumption
are checked before output. Six padded original raw records establish zero
padding to align the whole decoded buffer to four bytes. Explicit opacity is
preserved (opaque black stays opaque), BGR converted losslessly to RGB/alpha255;
transparent pixels have zero RGBA. Anchor values remain raw u16 without guessing
signed/runtime meaning. Complete 615-file images-v1 bundle installs via sibling
staging/rename; failures clean staging, repeat runs verify all names/bytes and
refuse modified/incomplete/extra content or symlinks. PNG compressed bytes may
differ between zlib versions; RGBA hashes remain stable. Unexpected/write faults
use the existing detached optional FF_FAULT_REPORT_URL reporter with version/
platform/exception class; malformed input is not reported, no endpoint in source.

Validation: compileall and all33 unittest cases pass with pinned external reader
6e178b9470206f71871417dec852fbfa24cd01b9 and local original enabled. Every original
PNG pixel/alpha matches external KlikBack parse_record/decode_rows; independent
source slot-table reads verify record hashes and raw anchors. Synthetic known
RGB/alpha plus literal/repeated/black pixels, malformed headers/pointers/runs,
limits, padding/tails, late invalid entries, atomic write/rename failures, changed
bundles, symlinks and fault classification exercised. Independent Pillow9.4.0
loads all614 PNGs with matching dimensions/mode/RGBA hashes. Executed red/blue
swap negative control fails both intended synthetic/original assertions; source
restored byte-exact before positives. CLI twice verifies identical bundle;
original SHA-256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0,
input unchanged. Actual agent ./node_modules/.bin/tsc --noEmit passed. Evidence:
agent state data/furries/image-dump/ (logs, oracle counts, fingerprints); original
content remains ignored/private.

Combined furries-exporter-spec stays started/sol. Global event containers/opcode
and parameter semantics, object-to-image animation mapping, arena JSON and an
observation-backed behaviour spec remain. No engine/release/Windows/Deck/hardware
claim, new schedule or second slice. Source delivery/CI result will be recorded
below; no separate CI continuation is scheduled by this tick.


Delivery of preceding image slice: source6666409ae186e8effb6df03a60acabf7ded0f1ef
passed CI38360137087, job115172114787:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38360137087 . Existing
snapshot and downloaded job log verify actual source/reader checkout and Python3.10
all33 cases (29 pass/four original fixtures skipped); all33 passed locally.
No continuation or in-flight work remained when this tick began. This closes
the preceding note's missing delivery paragraph without repeating that slice.

2026-10-13: Sol tick t_mv6isc229vpil, one bounded M0 frame-layout storage slice.
Clean main, fetched origin, no open PRs/issues or in-flight work at start; direct
main follows the repo convention. tools/frame_layout.py and docs/FRAME-LAYOUT.md
export ignored frame-layout.json with all raw frame headers and placement
pointer tables/32-byte records. Unused slots, aliases, reversed pointer order,
empty/missing/repeated blocks and both header shapes remain distinct. Pointers
are relative to the record area after the table; they are not absolute block
offsets. Unknown record/header fields are preserved without guessing x/y,
object IDs, collision, draw order or spawns. This is an arena-decoder prerequisite,
not completed arena JSON or a behaviour spec.

Strict counts, aligned/in-bounds pointers, complete record sizes and full
referenced-byte coverage validate before atomic file replacement. Symlinks
are refused, failed writes retain the old file and clean temporary files.
Unexpected/write faults use detached optional FF_FAULT_REPORT_URL reporting
with version/platform/exception class only; input errors are not reported.
No private endpoint, original data or graphics are committed/published.

Validation: compileall and all41 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and local original enabled. All13 frame
headers/all12 placement blocks reconstruct byte-for-byte; direct source-table
reads verify each of10141 slots and its referenced32-byte record (7968 distinct
records). Supported dialect, pointer origin and fixed record extent established
against every original block; no universal-format claim. Synthetic reversed
order/alias/gap fixtures, malformed sizes/pointers/unreferenced data, late invalid
blocks, atomic write failures, symlinks and fault classification exercised.
Executed reversed-record-mapping negative control fails the two intended
synthetic/original assertions; restored source before all41 positive cases.
An earlier all-zero mapping control was rejected by storage validation itself;
its log is retained separately, not claimed as an assertion probe.
Both CLI runs produce byte-identical JSON; input hash remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0,
unchanged. Evidence: agent state data/furries/frame-layout/; generated original
metadata stays ignored/private. Actual agent ./node_modules/.bin/tsc --noEmit passed after restoring omitted
dev dependencies with npm ci --include=dev --ignore-scripts; agent source and
lockfile unchanged. Source delivery/CI observations will be appended below.

Combined furries-exporter-spec remains started/sol. Placement/header semantics,
global-event containers/opcodes/parameters, animation mapping, arena geometry/
spawns and observation-backed behaviour remain open. No engine, release,
Windows/Deck/hardware claim, new schedule or second slice.
