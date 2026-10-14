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


Delivery: tested source bfebb97ac3a16cfb2bf72027e6598d84a73f81cf pushed main.
CI38382394176 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38382394176 . Downloaded
job115245767284 log verifies actual source checkout, pinned reader SHA and
Python3.10 all41 cases (36 pass/five local-original fixtures explicitly skipped).
All41 passed locally with the original enabled. CI snapshots/logs accompany
local evidence in data/furries/frame-layout/. Source fingerprints still match;
this delivery update is Markdown only. No in-flight work or CI continuation.
Combined exporter/spec remains started/sol; no release or second slice.

2026-10-13: Sol tick t_mv6j568mdyo0f, one bounded M0 active animation/image-handle
slice. Clean main/fetched origin, no open PRs/issues or in-flight work at start;
direct main follows the repo convention. tools/animation_dump.py and
docs/ANIMATIONS.md export ignored animations.json with all active payload bytes,
16 animation/32 direction slots, raw relative pointers, absent values/aliases,
ordered image handles and opaque headers/gaps/prefix/tail. Global definition
storage and reference-only local slots remain separate; no guessed resolution,
animation names/direction angles, timing/looping/selection or behaviour claim.
Occupied image handles validate against all retained image banks, without
selecting a runtime bank when repeated banks are present.

Structural evidence comes from pinned KlikBack icon_census.sprite_first_frame
and unprotect._active_animation_end; our decoder is independently implemented.
Animation region's u16 length verified on all83 original active payloads;
unparsed gaps and80-byte tails retained unchanged. All131 present animations,
256 directions and940 image references checked by independent source-word
reads; first image of each payload also agrees with KlikBack's icon helper.
815 local active definitions have no data and stay unresolved. Unsupported
signatures/extents, pointers into headers/tables, partial/incompatible overlaps,
truncation/counts and unoccupied image handles fail before any output write.
Atomic replacement, failure cleanup, symlink refusal and detached optional
private FF_FAULT_REPORT_URL reporter follow the existing contract; fault payload
has only version/platform/exception class. No endpoint/original content published.

Validation: compileall and all49 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Eight new cases
cover known ordered/repeated handles, aliases/gaps/raw headers, empty/absent
sets/zero-frame directions, local/global/deleted/reference-only slots, repeated
banks, invalid late data, malformed pointers/counts/extents, atomic write failures,
symlinks and fault classification. Executed reversed-image-order negative control
fails the two intended synthetic/original assertions; restored byte-exact before
all49 positives. Both CLI runs byte-identical and original unchanged with SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/animation-dump/. Actual agent
./node_modules/.bin/tsc --noEmit passed before commit; source delivery/CI
observations follow below.

Combined furries-exporter-spec stays started/sol. Other object artwork/global
reference resolution, event/global/placement semantics, arena geometry/spawns
and observation-backed behaviour remain open. No engine, release, Windows/Deck/
hardware claim, new schedule or second slice; no separate CI continuation.

Delivery: tested source acfb934574a7f118b6cca9e2ebac7d54ebe3a926 pushed main.
CI38383463499 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38383463499 . Downloaded
job115249342174 log verifies actual source/reader checkout SHA, Python3.10.22,
compileall and49 cases (43 pass/six local-original fixtures explicitly skipped).
All49 ran locally with original enabled. Saved source/docs/test hashes still
match; verification.json and CI snapshots/log accompany local evidence in
data/furries/animation-dump/. This delivery update is Markdown only; tested
source unchanged. No in-flight work or CI continuation remains. Combined
exporter/spec stays started/sol; no release or second slice.

2026-10-13: Sol tick t_mv6ji17nf2fh1, one bounded M0 backdrop-header artwork
slice. Clean main/fetched origin, no open PRs/issues or in-flight work at start;
direct main follows the repo convention. tools/backdrop_dump.py and
 docs/BACKDROPS.md export ignored backdrops.json with ordinary/quick-backdrop
image handles, editor fill colors/orientation and complete raw68-byte headers.
All definition slots, global/local headers, deleted/other types, bank gaps and
repeated/empty/missing lists/banks remain distinct. Used image handles retain
all matching bank segment IDs; solid/gradient image words stay raw and unused.
No runtime bank or global/local definition is guessed: local global-flagged
headers can carry different artwork words than global definitions.

Pinned KlikBack source_handle/quick_backdrop_icon supply independent editor-art
evidence for image u16 at54, quick fill byte32, COLORREF words24/28 and gradient
orientation bit0x10. Our decoder is independently implemented. Colors preserve
all raw32 bits, RGB excludes the high byte without interpreting it as alpha.
Unknown quick fill values/flags, malformed headers and unoccupied used image
handles fail before output; unused words do not require bank membership.
Atomic replacement/failure cleanup/symlink refusal and detached optional private
FF_FAULT_REPORT_URL handling follow existing exporters. Fault payload has only
version/platform/exception class; no endpoint or original content committed.

Validation: compileall and all56 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and local original enabled. Seven new
cases cover known images/mosaics/solid/both gradient axes, raw high COLORREF
bytes, unused unoccupied words, all definition slots, repeated/empty banks,
missing/empty lists, local data blocks, bad sizes/types/fills/used handles,
late invalid objects before write, atomic failures, symlinks and fault handling.
All410 original headers match source byte-for-byte:352 ordinary images,
30 mosaics,28 vertical gradients,382 used image references. External icon
source_handle agrees on every stored image word; all58 quick color pairs match
separate source-byte reads and external gradient icon endpoints agree. Solid/
horizontal fills have synthetic evidence only, not an original runtime claim.
Executed swapped-COLORREF red/blue control fails five intended assertions
(four synthetic fill subcases and original source/oracle verification); restored
source byte-exact before all56 positives. Both CLI runs produce identical JSON;
original unchanged, SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed. Evidence:
agent state data/furries/backdrop-dump/. Source delivery/CI observations follow.

Combined furries-exporter-spec stays started/sol. Display/text/extension artwork,
global reference resolution, event/placement semantics, arena geometry/spawns
and observation-backed behaviour remain open. Editor-art fields do not establish
runtime rendering, dimensions, collision or a playable engine. No release,
Windows/Deck/hardware claim, new schedule, continuation or second slice.

Delivery: tested source1a29f3e08619b9caef86874be47df482783cacba pushed main.
CI38384593082 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38384593082 . Downloaded
job115253119587 log verifies actual source/reader checkout SHA, Python3.10.22,
compileall and56 cases (49 pass/seven local-original fixtures explicitly skipped).
All56 ran locally with original enabled; saved source/docs/test hashes still
match. Verification/CI snapshots/job log accompany local evidence in
data/furries/backdrop-dump/. This delivery update is Markdown only; tested
source unchanged. No unfinished implementation or CI continuation remains.
Combined exporter/spec stays started/sol; no release or second slice.

2026-10-13: Sol tick t_mv6juvpmhj7fs, one bounded M0 score/lives/counter
artwork-storage slice. Clean main/fetched origin, no open PRs/issues or in-flight
work at start; direct main follows the repository convention. tools/display_dump.py
and docs/DISPLAYS.md export ignored displays.json with original definition slots,
all display payload bytes, counter attribute storage and ordered sections/image
lists. Global/local/reference-only definitions remain separate, without guessing
player ownership, numeric rendering, attribute meanings or global resolution.

SCRE/LIVE/CNTR at42 and counter attribute extent at46 have external editor-art
evidence in pinned KlikBack icon_census.display_first_frame. Contiguous section
lengths and counted lists (count+6/image words+8) were inferred and verified on
all27 original payloads/33 sections. Only modes1/4 are interpreted as image
lists; other modes stay raw/null, including all13 original counter mode0 and
both mode3 sections. The local original establishes4 score,2 lives,21 counter
payloads and178 image refs; all110 reference-only definitions remain unresolved.
Separate source-word reads verify every list/order, and first images agree with
the independent editor icon helper. Raw prefix/attributes/sections reconstruct
every payload byte-for-byte. Other Clickteam dialects/runtime semantics unproven.

Strict signatures/attribute and section extents/counts/trailing bytes/occupied
handles validate before atomic replacement. All candidate bank identities remain
explicit; unknown-mode words are not validated as image handles. Empty lists
remain distinct from opaque modes and reference-only objects. Unexpected/write
faults use detached optional private FF_FAULT_REPORT_URL handling with version/
platform/exception class only; malformed input is not reported. No private URL,
original assets or generated metadata are committed/published.

Validation: compileall and all64 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Eight new cases
cover three signatures, ordered/repeated/multiple lists, opaque/empty sections,
counter attributes, global/deleted/reference-only slots, bank gaps/repeated banks,
missing/empty object lists, malformed extents/counts/tails, late bad data before
save, atomic failure cleanup, symlinks and fault classification. Executed reversed
image-order negative control fails five intended assertions (original/container/
all three synthetic signatures); source restored before all64 positives. Two
CLI runs are byte-identical; original unchanged, SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. Evidence:
agent state data/furries/display-dump/; source delivery/CI result follows below.

Combined exporter/spec remains started/sol: text/font/extension artwork,
global/event/placement semantics, arena geometry/spawns and observation-backed
behaviour still open. No playable engine, release, Windows/Deck/hardware claim,
new schedule, continuation or second slice.

Delivery: tested source12f7a1f1326adbbe2f3d69bf309ba551224ae383 pushed main;
CI38385799400 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38385799400 . Downloaded
job115257160186 log verifies actual source/reader checkout SHA, Python3.10.22,
compileall and64 cases (56 pass/eight original fixtures explicitly skipped).
All64 passed locally with original enabled; saved source/docs/test hashes still
match. Verification/CI snapshots/job log accompany data/furries/display-dump/.
This delivery update is Markdown only; tested source unchanged. No unfinished
implementation or CI continuation; exporter/spec remains started/sol.

2026-10-13: Sol tick t_mv6k7rcknd5mk, one bounded M0 global-event storage
slice. Clean main/fetched origin, no open PRs/issues or in-flight work at start;
direct main follows the repository convention. tools/event_dump.py now emits
schema2/event-dump/2 with ordered global rows/conditions/actions/raw parameters
in events.json and readable events.txt. All existing frame JSON fields and
frame text (apart from the version line) match the previous tested exporter.
Global payload fingerprints/raw bytes/segment IDs remain, with preserved header,
program extents and intervening opaque editor bytes. docs/EVENTS.md documents
migration: unsupported global containers are now refused rather than silently
exported as opaque. No frame/global execution order or opcode semantics guessed.

Observed global dialect has40-byte header, total u32 at0, header extent at8,
program offset at12/size at16. The single original segment is63602 bytes:
9876 intervening opaque bytes, then53686 program bytes at9916. All398 rows,
765 conditions,968 actions and1475 parameters reconstruct byte-for-byte;
external pinned KlikBack event_groups agrees on every row offset/length.
Header interpretation is observation-backed against this one original, not an
independently established universal container spec. Other header words stay raw;
no guessed editor fields or global reference resolution. Original has no font
bank/type3 or4 text/question payloads; no text/font implementation invented.

All input validates before output. Bad totals/header extents/pointers/sizes,
records/parameters/counts/terminators and late-invalid repeated global segments
fail exit2 before either JSON/text write or reporting. Existing atomic writer,
symlink protection and detached optional FF_FAULT_REPORT_URL fault handler
remain; unexpected/write faults report only version/platform/exception class.
No private endpoint, original data or generated metadata committed/published.

Validation: compileall and all72 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Eight new tests
cover ordered parameters/unknown header/editor bytes, empty programs/regions,
missing/repeated global segments, malformed/overflow-sized extents, invalid
rows, readable output and late-invalid input before save. Executed reversed-
global-row negative control fails four intended synthetic/text/container/original
assertions; source restored byte-exact before all72 positives. Both CLI formats
run twice with identical files; original unchanged, SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. Evidence:
agent state data/furries/global-events/; source delivery/CI result follows below.

Combined exporter/spec stays started/sol: global execution/opcode/parameter and
object/placement semantics, extension data, arena geometry/spawns and observed
behaviour remain open. No playable engine, release, Windows/Deck/hardware claim,
new schedule, continuation or second slice.

Delivery: tested source a4241729052b1d36d5e1cc9ca72827cf42fe6781 pushed main;
CI38386873916 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38386873916 . Downloaded
job115260724596 log verifies actual source/reader checkout SHA, Python3.10.22,
compileall and72 cases (63 pass/nine original fixtures explicitly skipped).
All72 passed locally with original enabled; saved source/docs/test hashes still
match. Verification/CI snapshots/job log accompany data/furries/global-events/.
This delivery update is Markdown only; tested source unchanged. No unfinished
implementation or CI continuation; combined exporter/spec stays started/sol.

2026-10-13: Sol tick t_mv6kkmohpwx3u, one bounded M0 frame-event local
reference annotation slice. Clean main/fetched origin, no open PRs/issues or
in-flight work at start; direct main follows the repository convention.
Event-dump/3/schema3 retains all existing event bytes/fields and adds candidate
object names/types/flags/actual object-list block IDs to frame records. Positive
types with ordinary references below0x4000 match slots only in that frame;
multiple lists, missing/deleted/type-mismatched slots remain explicit. Zero/
negative types and encoded references stay unresolved; global programs are not
assigned a guessed frame. Local global-flagged/reference-only headers remain
storage candidates, not resolved runtime artwork or behaviour.

Pinned KlikBack columns_from_events/referenced_objects establish the ordinary
reference-to-local-slot mapping and separate encoded references. Independent
source-word reads/external object definitions/editor columns verify all7573
original frame records:4613 local matches,2958 non-object types,2 encoded refs.
Unknown opcode/parameter meanings, global/qualifier/shortcut resolution,
parameter-embedded references and execution order remain unchanged. Readable
REFERENCE lines JSON-escape original names, preserving quotes/control characters
without creating false event lines. docs/EVENTS.md describes schema migration.

Validation: compileall and all80 local unittest cases pass with pinned reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Eight new cases
cover local flags/names/block identities, extension types/boundary handles,
non-object/encoded refs, missing/deleted/mismatched/ambiguous slots, separate
frame scopes/repeated lists, readable escaping, late-invalid input before write
or reporting, and all original candidates/lossless programs. Existing atomic
write/symlink/fault-classification checks pass; detached optional private
FF_FAULT_REPORT_URL reporting remains unchanged with no endpoint in source.
Executed off-by-one slot negative control fails nine intended assertions in
eight executed cases; source restored byte-exact before all80 positives.

Previous-source comparison proves all existing frame/global JSON fields/order/
raw bytes unchanged after removing only new annotations/coverage/version; text
matches after removing new REFERENCE lines and normalizing version. Both CLI
formats run twice with identical outputs; original unchanged, SHA-256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed. Evidence:
agent state data/furries/event-references/; generated original metadata ignored/
private. Source delivery/CI observation follows below within this turn.

Combined exporter/spec remains started/sol: event/parameter/global/placement
semantics, extension data, arena geometry/spawns and observation-backed behaviour
remain open. No playable engine, release, Windows/Deck/hardware claim, new
schedule, continuation or second slice.

Delivery: tested source04205ed51974097625c9ec4cbd339d2c40b1f7ce pushed main;
CI38388100089 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38388100089 . Downloaded
job115264775154 log verifies actual source/reader checkout, Python3.10.22,
compileall and80 cases (70 pass/ten original-file fixtures explicitly skipped).
All80 passed locally with original enabled; saved source/docs/test hashes still
match. Verification/CI snapshots/job log accompany data/furries/event-references/.
This delivery update is Markdown only; tested source unchanged. No unfinished
implementation or CI continuation; combined exporter/spec remains started/sol.


2026-10-13: Sol tick t_mv6kxh29r3vv0, one bounded M0 combined research-export
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. tools/export_project.py and
 docs/PROJECT-BUNDLE.md compose all existing supported exports from one input
read into ignored export/<sha>/research-v1/. Nine component files/text plus
614 PNGs,17 WAVs,2 unchanged MIDI files and top-level manifest make643 files.
All642 component/media bytes equal the previously verified standalone outputs;
individual outputs and original input remain unchanged. Component schemas,
media names/relative references and bank gaps/repeated/empty/missing data stay
intact. Top manifest supplies source/reader identity, component versions and
sorted hashes/lengths for every other file, without circular self-hashing.

Every component validates before any output creation; fingerprint disagreement
is an unexpected implementation fault. A late unsupported image rejects the
whole export. One sibling staging-directory rename installs the complete tree;
write/rename failures clean staging. Repeat runs verify every name/byte without
repairing changed/missing/extra files, directory substitutions or symlinks.
Source digest and flat filenames validate before directory creation. Existing
bundles produced by changed exporter/zlib bytes require explicit move-aside.
Private optional detached FF_FAULT_REPORT_URL handling identifies export-project/1
and sends only version/platform/exception class; malformed input/output conflicts
are not reported. No private endpoint/original content is committed/published.

Validation: compileall and all89 local tests pass with pinned external reader
6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Nine new cases cover
all component/media integration, independent synthetic WAV/PNG readback,
lossless frame/global events and placement reconstruction, repeated/gapped/empty
banks, absent frames, late-invalid input before save/report, component identity
mismatch, immutable-tree conflicts, invalid paths/symlinks, actual late write and
rename failures, fault classification and complete original installation/readback.
Executed omitted-MIDI negative control fails two intended assertions in two
executed synthetic/original cases; source restored byte-exact before final89
positives. CLI twice verifies the identical643-file tree, all642 prior component
files match byte-for-byte and are unchanged, and original SHA-256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed after restoration.
Evidence: agent state data/furries/research-bundle/; source delivery/CI follows.

Combined furries-exporter-spec remains started/sol. This is an atomic composition
of existing research tools, not completed arena JSON/behaviour spec or an engine.
Event/parameter/global runtime and placement semantics, geometry/spawns and
observation-backed gameplay still open. No release, Windows/Deck/hardware claim,
new schedule, CI continuation or second slice.

Delivery: tested source e4e9eaf69c12ea8b51ca42012170f2c68f1cb746 pushed main;
CI38389452777 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38389452777 . Downloaded
job115269329841 log verifies actual source/reader checkout, Python3.10.22,
compileall and all89 cases (78 pass/eleven original-file fixtures skipped).
All89 passed locally with original enabled; saved source/docs/test hashes still
match. Verification/CI snapshots/job log accompany data/furries/research-bundle/.
This delivery update is Markdown only; tested source unchanged. No unfinished
implementation or CI continuation. Combined exporter/spec remains started/sol.

2026-10-13: Sol tick t_mv6ln7z3tnnnu, one bounded M0 editor-event-group
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event_dump/4/schema4 adds per-row
editor open/close/event annotations, nesting and matching storage row IDs,
per-program balance diagnostics and supported stored titles in JSON/readable
text. Global/frame stacks remain separate; unmatched/unclosed markers and
unknown title shapes remain explicit without repairing or discarding bytes.

Pinned KlikBack common/reconstruct_event_test.py::group_marker establishes
first-condition type -1/opcode -10/-11 marker bytes; common/global_event_reconstruct.py
::group_records independently verifies type38 title offset/80-byte extent.
The implementation is ours. Supported parameter is88 bytes: two opaque raw u16
words then80 title bytes. Prefix meanings/flags/activation/identity stay unknown;
Latin-1 is only a reversible byte view, not an asserted source code page. Complete
field including nonzero NUL tails is retained. All41 original pairs balance:
21 frame groups/20 global groups, all flat. Named movement/animation/underwater/
weapon sections are navigation evidence, not proof of their runtime behaviour.

Validation: compileall and all96 local tests pass with original enabled and
pinned reader6e178b9470206f71871417dec852fbfa24cd01b9. Seven new cases cover nested
pairs/scopes, empty/full-width/non-ASCII/control-character titles and NUL tails,
unknown/duplicate title shapes, first-system-condition marker specificity,
unbalanced programs/separate stacks, duplicate opaque words and all original
names/source fields/pairs versus external helpers. All previous JSON raw fields
and frame reference annotations equal prior source after removing only additions/
version; old text matches after removing GROUP/GROUP_STRUCTURE lines and version.
Raw frame/global byte reconstruction remains exact. Existing late-invalid input,
atomic/symlink/fault-classification tests pass; detached optional private reporter
unchanged, no URL/assets/metadata committed or published.

Executed title-offset+1 control fails four intended assertions in seven executed
cases. Source restored byte-exact. The first post-control suite exposed cached
mutant Python bytecode after a same-size restore within one timestamp second;
force compileall cleared it, all96 positives reran successfully, and generated
standalone/bundle exports were corrected and their title fields independently
rechecked. Keep that failure log; force bytecode regeneration after future
same-size Python controls. Existing immutable research-v1 refused changed bytes
without mutation; old bundle preserved privately, corrected643-file bundle
installed/repeated. Only events.json/events.txt/manifest.json change; all640
other files remain byte-identical. All three CLIs repeat byte-identically;
original unchanged SHA25698c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. Evidence:
agent state data/furries/event-groups/; source delivery/CI follows within this turn.

Combined exporter/spec remains started/sol: activation/gameplay opcode/parameter/
global execution and placement semantics, arenas/spawns and observed behaviour
remain open. No engine/release/Windows/Deck/hardware claim/new schedule/CI
continuation/second slice.

Delivery: tested source3b32c740708f3d2ba2b99a2b022465eb3d4da57f pushed main;
CI38391728150 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38391728150 . Downloaded
job115276903127 log verifies actual source/reader checkout, Python3.10.22,
compileall and all96 cases (84 pass/twelve local-original fixtures skipped).
All96 passed locally with original enabled; source/docs/test hashes still match.
Verification/CI snapshots/job log accompany data/furries/event-groups/. This
final delivery edit is Markdown only; tested source unchanged. No unfinished
implementation or CI continuation; exporter/spec remains started/sol.

2026-10-13: Sol tick t_mv6mcxqyvdqtz, one bounded M0 expression-token storage
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows the repository convention. event_dump/5/schema5 adds ordered
expression tokens and embedded object-slot candidates in JSON/readable text.
The six parameter types 15/22/23/45/52/53 and token traversal are supported by
pinned KlikBack common/reconstruct_event_test and event_object_registry helpers.
Only token storage/reference words are interpreted: prefix, suffix, operators,
literals, comparison/evaluation/global/runtime meanings remain opaque.

All 3868 original expressions (2461 type22/1400 type23/seven type45), 4485
tokens/22 codes and288 embedded object words reconstruct exactly and agree
with separate source reads/external reference traversal. All98 frame references
match external local definitions (17 expected-type matches/81 untyped candidates);
190 global references stay frame_context_unresolved. Missing/deleted/mismatched/
ambiguous/encoded references are explicit, with all block identities retained.
Raw token spans, u16 prefix, first zero terminator and arbitrary suffix bytes
are preserved. No arithmetic or gameplay semantics, frame for globals or
universal editor-dialect claim is invented. Supported expression shapes now
validate strictly before any JSON/text/bundle output; unsupported lengths,
truncated object tokens/missing terminators fail exit2 without fault reporting.
The old synthetic two-byte type22 placeholder now has a valid empty terminator.
Existing detached optional private FF_FAULT_REPORT_URL handling stays unchanged;
no secret endpoint, original data/assets or generated metadata committed/published.

Validation: force compileall and all104 local unittest cases pass with pinned
reader6e178b9470206f71871417dec852fbfa24cd01b9 and original enabled. Eight new
cases cover all six types/condition+action/frame+global programs, token order/
unknown codes/empty expressions/opaque tails, reference status/type boundaries,
separate frame scopes/repeated lists, escaping, late-invalid input before any
save/report and original source/ext-helper/candidate identity/lossless proof.
Executed reference-offset+1 control fails three intended assertions in eight
executed cases; source restored byte-exact and compileall -f forced before all104
final positives. Existing atomic write/symlink/fault-classification checks pass.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit.

Previous-source comparison proves all existing raw JSON fields, object reference
and group annotations unchanged after removing only expression additions/version;
old readable text is identical after removing EXPRESSION lines/version. Old
immutable research-v1 bundle refused changed bytes without mutation, preserved
privately before regenerated643-file bundle installation/repeat. Only events.json,
events.txt and manifest.json change; all640 other files remain byte-identical.
Standalone JSON/text and bundle CLIs run twice with identical files. Original
unchanged SHA25698c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/event-expressions/; source delivery/CI follows
within this turn. No schedule or CI continuation created.

Combined furries-exporter-spec stays started/sol: opcode/parameter evaluation,
global execution, placement fields/arena geometry/spawns and observation-backed
behaviour remain open. No playable engine, release, Windows/Deck/hardware claim
or second slice.

Delivery: tested sourcea59b24d9a16d3dd7fd299f0c46bdd66b25d8ce2f pushed main;
CI38393987245 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38393987245 . Downloaded
job115284466413 log verifies actual source/reader checkout, Python3.10.22,
compileall and all104 cases (91 pass/thirteen local-original fixtures skipped).
All104 passed locally with original enabled; all saved source/docs/test hashes
still match. CI snapshot/log and verification accompany data/furries/event-expressions/.
This final delivery edit is Markdown only; tested source unchanged. No unfinished
implementation, new schedule or CI continuation. Combined exporter/spec stays
started/sol; no release or second slice.

2026-10-13: Sol tick t_mv6tut0815kyf5, one bounded M0 position-parameter
reference slice. Clean main, fetched origin, no open PRs/issues or in-flight
work at start; direct main follows the repository convention. event-dump/6,
schema6 adds position_reference_storage for types9/16/18/21, with position
reference words at payload0 and creation targets at payload24 for9/18. Pinned
KlikBack event_object_registry traversal and reconstruct_event_test remapper
establish minimum sizes/word locations/role-specific absolute sentinels.
The original has1263 supported parameters and2523 reference words:2520
frame-local untyped candidates/three unresolved globals. Type21 is synthetic
only. No containing-record type is imposed on these independent references.

Absolute position0xFFFE/0xFFFF stays explicit and candidate-free; creation
targets with those words remain unresolved. Local missing/deleted/ambiguous/
encoded slots, reference-only/global-flagged headers and actual object-list
block identities remain explicit. Global programs acquire no guessed frame.
Raw coordinates, flags, relative-position selection, shoot speed and all other
bytes remain opaque; no opcode/execution/geometry/spawn/gameplay claim.
Readable POSITION_REFERENCES lines JSON-escape names/control characters.
Supported truncated shapes now refuse exit2 before JSON/text/bundle output
or fault reporting. Existing detached optional FF_FAULT_REPORT_URL handler,
atomic writes/symlink protection and immutable bundle rules remain unchanged.
No private endpoint or original data/assets/metadata committed or published.

Validation: force compileall and all112 local unittest cases pass with original
enabled and pinned reader6e178b9470206f71871417dec852fbfa24cd01b9. Eight new
cases cover all four types/condition+action/frame+global containers, exact
raw payload preservation including arbitrary tails, both absolute sentinels,
strict minimum lengths, unknown types, names/separate frames/multiple lists,
deleted/missing/encoded slots, late invalid input before writes/reporting,
independent remapper/source-word/traversal/candidate checks on the original.
Executed creation-target offset+1 control fails five intended assertions in
eight cases; source restored byte-exact and compileall -f forced before final
positives. Actual agent ./node_modules/.bin/tsc --noEmit passed before commit.

All previous raw JSON/reference/group/expression annotations match prior source
a094d62 after removing only additions/version; text matches after removing new
lines/version. Old immutable research bundle refused changes without mutation,
preserved privately before updated643-file installation/repeat. Only events.json,
events.txt and manifest.json change;640 other files remain byte-identical.
JSON/text/bundle CLIs repeat identically; original unchanged SHA256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/event-positions/. Source delivery/CI follows
within this turn; no schedule or CI continuation created.

Combined exporter/spec stays started/sol: opcode/parameter/global evaluation,
placement coordinates/arena geometry/spawns and observed behaviour remain open.
No playable engine/release/Windows/Deck/hardware claim or second slice.

Delivery: tested source8e59ceaecd3044b3a75f7ecec7a19659f9260e20 pushed main;
CI38422195826 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38422195826 . Downloaded
job115382156017 log verifies actual source/reader checkout, Python3.10.22,
compileall and112 cases (98 pass/fourteen local-original fixtures skipped).
All112 passed locally with original enabled; saved source/docs/test hashes
still match. CI snapshot/job log and verification accompany
 data/furries/event-positions/. This delivery edit is Markdown only; tested
source unchanged. No unfinished implementation/schedule/CI continuation;
exporter/spec stays started/sol, no release or second slice.

2026-10-13: Sol tick t_mv6u7nop17tbb0, one bounded M0 event-audio bank
reference slice. Clean main, fetched origin, no open PRs/issues or in-flight
work at start; direct main follows the repository convention. event-dump/7,
schema7 adds sound/music parameter handle words and application-bank slot
candidates to JSON/readable text. Pinned KlikBack6e178b9 converter establishes
parameter types6/7 and u16 at payload0; a separate executed converter probe
confirms only that exact word is cleared to the respective editor value.

Frame/global programs share application audio banks partitioned by kind. Missing
slots/empty or absent banks and duplicate-bank ambiguity stay explicit; handle0
is a valid slot,0xFFFF receives no invented sentinel meaning. Candidate segment/
slot/offset/length/record hash joins the existing audio manifest and filenames;
no unsupported media filename is guessed. All other parameter bytes stay opaque,
with no name decoder, opcode playback/looping/timing/volume or runtime claim.
Direct source table/word reads verify all891 original references (870 sound,
21 music) against independently exported audio entries. Each has exactly one
candidate; original parameter/bank name-prefix bytes independently corroborate
slot identity without being decoded by production code.

Validation: force compileall and all120 local tests pass with original enabled
and pinned external reader6e178b9470206f71871417dec852fbfa24cd01b9. Eight new
cases cover both types/roles/frame/global scope, minimum handle lengths and
opaque tails, kind separation, gaps/absent/empty/repeated banks, slot0/0xFFFF,
exact external-converter changes, direct original words/tables/media identities,
late-invalid rejection before JSON/text/bundle output/reporting and integrated
immutable bundle/media readback. Executed candidate-slot+1 control fails three
intended assertions in eight executed cases; source restored byte-exact and
compileall -f forced before final positives. Existing atomic/symlink/fault
checks pass; optional detached FF_FAULT_REPORT_URL handler remains unchanged,
no private endpoint/original content/metadata committed or published.

All prior raw JSON and object/group/expression/position annotations match prior
source b97bb39 after removing only additions/version. Old text matches after
removing AUDIO_REFERENCE lines/version. Old immutable research bundle refused
changed bytes without mutation and was preserved privately before updated643-
file installation/repeat. Only events.json/events.txt/manifest.json change;
640 other files including all audio/images stay identical. JSON/text/bundle
CLIs repeat identically; original SHA256 unchanged
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. Evidence:
agent state data/furries/event-audio/. Source delivery/CI follows within this
turn; no schedule or continuation created.

Combined furries-exporter-spec remains started/sol: opcode/parameter/global
evaluation, placement coordinates/arena geometry/spawns and observation-backed
behaviour still open. No playable engine/release/Windows/Deck/hardware claim
or second slice.

Delivery: tested source6e0c7162c3a5a01b6bddb80bbe9983d14a214f07 pushed main;
CI38423753004 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38423753004 . Downloaded
job115387584333 log verifies actual source/reader checkout, Python3.10.22,
compileall and120 cases (105 pass/15 original-file fixtures explicitly skipped).
All120 passed locally with original enabled; saved source/docs/test hashes
still match. CI snapshot/job log and verification accompany
 data/furries/event-audio/. This delivery edit is Markdown only; tested source
unchanged. No unfinished implementation/schedule/CI continuation; combined
exporter/spec remains started/sol, no release or second slice.

2026-10-13: Sol tick t_mv6ukje319lmmn, one bounded M0 object-parameter
reference slice. Clean main, fetched origin, no open PRs/issues or in-flight
work at start; direct main follows the repository convention. event-dump/8,
schema8 adds type1 object-parameter slot words (payload+2) and untyped same-frame
candidates to JSON/readable text. Pinned KlikBack6e178b9 registry independently
identifies type1/minimum10 bytes/parameter+6; executed editor-converter probes
remap only that payload word for both conditions and actions. No neighbour word
is guessed as a type or qualifier. Missing/deleted/ambiguous/encoded slots remain
explicit, including0xFFFE/0xFFFF with no invented sentinel; globals stay unresolved.
All974 original references agree with direct source words, independent registry
traversal and same-frame definitions:760 local candidates/214 unresolved globals.
Opcode/collision/selection/qualifier/evaluation/runtime meanings remain unknown.

Validation: force compileall and all128 local tests pass with the original and
pinned reader enabled. Eight new cases cover both roles/scopes, raw tails, short
shapes, slot boundaries, arbitrary adjacent words, missing/deleted/multiple lists,
escaped names, converter/registry agreement, late invalid input refusal before
JSON/text/bundle writes/reporting, integrated bundle and original source proof.
Executed reference-word offset+1 control fails five intended assertions in eight
executed cases; source restored byte-exact and compileall -f forced before final
positives. Actual agent ./node_modules/.bin/tsc --noEmit passed before commit.
Existing optional detached FF_FAULT_REPORT_URL handler, atomic/symlink guards and
immutable bundle rules remain unchanged. No endpoint or original data/assets/
metadata committed or published. Evidence: data/furries/event-object-parameters/.

Prior raw event fields and all earlier annotations remain identical after removing
only new fields/version; prior readable text matches after removing new lines/
version. Old immutable bundle refuses changed output without mutation and is
preserved privately before updated643-file installation/repeat. Only events.json,
events.txt/manifest.json change;640 other files remain byte-identical. JSON/text/
bundle CLIs repeat identically; input SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Source delivery/CI result follows within this turn; no continuation or schedule.

Combined furries-exporter-spec stays started/sol: opcode/global/parameter
semantics, placement coordinates/arenas/spawns and observed behaviour remain.
No playable engine, release, Windows/Deck/hardware claim or second slice.

Delivery: tested source bd404e4fcd397940bffcdc626a52634742bb0209 pushed main;
CI38424855740 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38424855740 . Downloaded
job115391440851 log verifies actual source/reader checkout, Python3.10.22,
compileall and128 cases (112 pass/sixteen original-file fixtures skipped).
All128 passed locally with original enabled; saved source/docs/test hashes
still match. CI snapshot/job log and verification saved with local evidence in
 data/furries/event-object-parameters/. This delivery edit is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.

2026-10-13: Sol tick t_mv6uxe9w1bwzcl, one bounded M0 event-group parameter
storage/equality slice. Clean main, fetched origin, no open PRs/issues or
in-flight work at start; direct main follows the repository convention.
event-dump/9/schema9 exports type39 payload u32/optional following u16/opaque
suffix, with explicit group-title stored-word candidates in JSON/readable text.
Pinned KlikBack converter establishes the first four bytes cleared only in
actions; synthetic probes and71 actual original rows execute that converter.
Conditions preserve their own word. Runtime addresses are never dereferenced
or treated as source offsets; activation/opcode/condition polarity stay unknown.

Candidates compare the complete payload+4 word to the second raw title-prefix
word on known-shape openings: this is byte equality, not authoritative group
resolution. A frame searches its own program plus application globals; a global
searches application globals. Scopes, actual frame/block/segment/row identities,
names and unmatched closes remain explicit. Duplicate/missing/partial keys,
unknown title shapes, unclosed groups and simultaneous local/global matches
are retained without selecting a winner or guessing sentinel/precedence rules.
All159 original parameters (115 actions/44 conditions) have one stored-word
candidate; separate source reads/external group markers/title spans verify
every word/candidate and preserve every parameter byte. This one-original
observation does not establish group execution or universal dialect semantics.

Validation: force compileall and all136 local tests pass with original and
pinned reader enabled. Eight new cases cover both roles/scopes, arbitrary tails,
partial/short shapes, zero/0xFFFF keys, repeated programs/multiple global segments,
duplicate/unknown/unclosed titles, escaped names, external converter probes,
late-invalid refusal before JSON/text/bundle writes/reporting and bundle repeats.
Executed key-offset4->2 control fails six intended assertions in eight executed
cases; source restored byte-exact and compileall -f forced before final positives.
Actual agent ./node_modules/.bin/tsc --noEmit passed. Existing optional detached
FF_FAULT_REPORT_URL handler, atomic/symlink guards and immutable bundle behavior
remain unchanged. No private endpoint/original content/metadata published or
committed. Evidence: agent state data/furries/event-group-parameters/.

Prior raw event fields and every earlier annotation remain identical after
removing only new fields/version; old text matches after removing GROUP_PARAMETER
lines/version. Old immutable research bundle refuses changed bytes without
mutation and is preserved privately before the updated643-file install/repeat.
Only events.json/events.txt/manifest.json change;640 other files stay identical.
JSON/text/bundle CLIs repeat identically; input SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Source delivery/CI follows within this turn; no continuation or schedule.

Combined furries-exporter-spec stays started/sol: runtime/opcode/parameter/global
evaluation, placement fields/arena geometry/spawns and observed behaviour remain
open. The placement field investigation found the external modern Inst/IPIn
writer is a different layout; no guessed CnC coordinates were committed.
No playable engine/release/Windows/Deck/hardware claim or second slice.

Delivery: tested source8823e097eecb67b1f8f83cef9d8902c466c793c0 pushed main;
CI38426502150 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38426502150 . Downloaded
job115397174104 log verifies actual source/reader checkout, Python3.10.22,
compileall and136 cases (119 pass/17 original-file fixtures explicitly skipped).
All136 passed locally with original enabled; all saved source/docs/test hashes
still match. CI snapshots/log and verification saved with local evidence in
 data/furries/event-group-parameters/. This delivery edit is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec stays started/sol, no release or second slice.


2026-10-13: Sol tick t_mv6va9ai1d4bmf, one bounded M0 action frame-target
storage/level-number probe slice. Clean main, fetched origin, no open PRs/issues
or in-flight work at start; direct main follows the repository convention.
event-dump/10/schema10 adds action parameter type26's u16 at payload0 and
lossless application segment7 word views to JSON/readable text. Independent
pinned KlikBack6e178b9 editor converter remaps exactly that action word;
conditions remain unannotated. Every table preserves segment/source identity,
full bytes/hash, ordered u16 views and an odd-byte suffix, without guessing a
count/header/terminator. Empty/absent/repeated tables remain distinct.

The raw target used as a table index is an explicitly named research probe,
not a resolved runtime destination. Missing/duplicate table slots remain
explicit; 0xFFFF targets/words have no invented sentinel rule, and candidates
contain no frame ID. Original has only two recognized actions, both global
object type-3/opcode2, target13. Its one28-byte/14-word table has slot13 raw
word1; this does not prove destination frame1 or one-based frame13. The pinned
reader's complete frame resolver reads later MMF chunk0x222B, not CnC segment7;
no cross-format mapping or transition behavior was borrowed.

Validation: force compileall and all144 local tests pass with the original and
pinned reader enabled. Eight new cases cover both scopes, action-only evidence,
boundary targets/opaque tails, missing/empty/odd/repeated tables, nonidentity
words, duplicate candidate identities, 0xFFFF indexing an actual available slot,
strict short-action refusal before JSON/text/bundle output or fault reporting,
source program/table reconstruction and two actual original converter probes.
Executed table-index+1 control fails three intended assertions in eight executed
cases; source restored byte-exact and compileall -f forced before positives.
Actual agent ./node_modules/.bin/tsc --noEmit passed before commit. Existing
optional detached FF_FAULT_REPORT_URL handler, atomic/symlink guards and immutable
bundle behavior stay unchanged. No private endpoint/original content/metadata
published or committed. Evidence: data/furries/event-frame-targets/.

All prior raw event fields/annotations/text lines match source089123a after
removing only additions/version. Older immutable bundle refuses changed bytes
without mutation and is preserved privately before updated643-file installation.
Only events.json/events.txt/manifest.json change;640 other files remain identical.
JSON/text/bundle CLIs repeat identically; input SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Source delivery/CI follows within this turn; no schedule or continuation created.

Combined furries-exporter-spec remains started/sol: runtime frame destinations,
opcode/global/parameter evaluation, placement/arena geometry/spawns and observed
behaviour remain open. No playable engine/release/Windows/Deck/hardware claim
or second slice.


Delivery: tested source0534df72accaa02fbb49bd580a07fd5ace30a69c pushed main;
CI38428228704 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38428228704 . Downloaded
job115403190806 log verifies actual source/reader checkout outputs, Python3.10,
compileall and144 cases (126 pass/eighteen original-file fixtures skipped).
All144 passed locally with original enabled; saved source/docs/test hashes
still match. CI snapshot/job log and verification saved with local evidence in
 data/furries/event-frame-targets/. This delivery update changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.


2026-10-13: Sol tick t_mv6vzza71faf6w, one bounded M0 integer-expression
literal slice. Clean main, fetched origin, no open PRs/issues or in-flight
work at start; direct main follows the repository convention. event-dump/11,
schema11 annotates exactly8-byte token0x00FF with signed32/raw-u32 values at
byte4, proven from the player's original executable's dispatcher and numeric
handler. Both roles/frame/global programs and all six expression types use it.
Unknown tokens/prefix/suffix/operators remain opaque; compound evaluation and
containing event/parameter meanings stay unresolved. Extended/short recognized
tokens exit2 before JSON/text/bundle output or fault reporting.

Primary evidence: original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.
Dispatcher0x42a474 selects table0x41b2b8 for type-1 and handler0x428823 for
opcode0; handler loads EAX from token+4 and clears numeric tag DX. Independent
Unicorn2.1.4 runs actual dispatcher AND lone-literal evaluator0x42a42e for
all3776 original tokens plus seven signed boundary cases:7566 executions,
matching result/tag/cursor/stack. TEXT_1 is marked PE DATA, so objdump -d misses
the runtime: use objdump -D -j TEXT_1. A newer Clickteam Java SDK corroborates
signed32 only; its wider0x0000FFFF code is explicitly NOT borrowed as a CnC
alias. SDK pin5f8f266/jar hash and disassembly remain private evidence.
This is isolated original instruction execution, not original gameplay or a
playable fork/Windows/Deck/controller acceptance claim.

Validation: force compileall and all151 local tests pass with original and
pinned KlikBack6e178b9. Seven new cases cover signed boundaries, mixed tokens,
unknown modern codes, unsupported literal extents, both roles/all expression
types/scopes, late-invalid refusal before every output/report, bundle repeats
and independent source/external token-walk original proof. Executed byte4->3
signed-value control fails four intended assertions in seven executed cases;
source restored byte-exact and compileall -f forced before final positives.
Actual agent ./node_modules/.bin/tsc --noEmit passes before commit. Existing
optional detached FF_FAULT_REPORT_URL fault handler, atomic/symlink protections
and immutable bundles remain unchanged. No private endpoint/original assets,
metadata, SDK code or original machine bytes are committed/published.
Evidence: agent state data/furries/expression-literals/.

All prior raw event fields/reference/group annotations match preceding source
da390a6 after removing only additions/version. Text matches after removing
literal annotations inside EXPRESSION JSON and new version/coverage sentence.
Prior643-file immutable bundle rejects changed bytes without mutation and is
preserved before regeneration;640 other component/media files stay identical.
JSON/text/bundle CLIs repeat identically; source SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Source delivery/CI follows within this turn; no schedule/continuation created.
Combined furries-exporter-spec remains started/sol: compound/global/opcode
semantics, placement/arena geometry/spawns and observed behaviour remain open.
No second slice or release.


Delivery: tested source589cb99d0c7e453eeae882ca13033523ddad4102 pushed main;
CI38431370537 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38431370537 . Downloaded
job115414109092 log verifies actual source/reader git log outputs, Python3.10,
compileall and151 cases (132 pass/nineteen original-file fixtures skipped).
All151 passed locally with original enabled; saved source/docs/test hashes
match. CI snapshots/logs and runtime oracle saved with local evidence in
 data/furries/expression-literals/. This delivery edit is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.


2026-10-13: Sol tick t_mv6wprad1hgrnp, one bounded M0 byte-string expression
literal slice. Clean main, fetched origin, no open PRs/issues or in-flight work
at start; direct main follows repository convention. event-dump/12/schema12
annotates only token0x03FF's NUL-terminated bytes at token+4, with byte hex,
reversible Latin-1 byte view, terminator offset and opaque post-NUL tail.
Encoding remains unknown; raw fields/ordering and integer/object/group/parameter
annotations remain unchanged. No compound evaluation, containing opcode, INI
access or global/gameplay meaning is inferred. Missing token-local NUL fails
exit2 before JSON/text/bundle writes or reporting; later terminators cannot
rescue a malformed token. Existing detached optional private fault reporter and
atomic/symlink/immutable output guards stay unchanged.

Primary proof: original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.
Dispatcher0x42a474 selects type-1 table0x41b2b8, opcode3 handler0x42881b;
that handler returns EDI+4/string DX tag1. Independent Unicorn2.1.4 execution
of dispatcher and lone-literal evaluator0x42a42e verifies pointer/byte value/
tag/next-token cursor/balanced stack for seven original tokens and seven
synthetic boundaries (28 executions). This runs original instructions in
isolation, not gameplay/file APIs. All original strings have one13-byte value;
no original machine bytes, data or metadata are committed or published.
Private evidence: agent state data/furries/expression-strings/.

Validation: forced compileall and all158 local tests pass with pinned
KlikBack6e178b9 and original enabled. Seven new cases cover empty/high/escaped
bytes, maximal u16 extent, post-NUL opaque tail, exact-code/mixed isolation,
all six expression types/both roles/scopes, readable escaping, lossless source
reconstruction, immutable repeat bundles, late-invalid refusal before every
output/report, and direct original source/external-token-walk proof. Executed
string-field offset4->5 control causes two intended assertion failures and
one bounded-NUL error in seven executed cases; restored byte-exact and forced
compileall before positives. Full suite initially caught stale schema/version
expectations; updated those assertions to12 without changing their behavior
checks. Actual agent ./node_modules/.bin/tsc --noEmit passed before commit.

All prior JSON fields match previous source21d83a7 after removing only string
annotations/coverage/version. Existing text matches after removing new string
annotations inside EXPRESSION JSON and updating banner/coverage sentence.
Prior643-file research bundle rejects changed bytes without mutation, preserved
before regeneration;640 other files unchanged. JSON/text/bundle CLIs repeat
identically; source project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Delivery and CI follow below within this tick; no schedule/continuation created.
Combined exporter/spec remains started/sol: compound/global/opcode semantics,
placement/arena geometry/spawns and observation-backed behaviour remain open.
No playable engine/release/Windows/Deck/hardware claim or second slice.


Delivery: tested source3dff3344248c427d58494bf9c012cf6096054f31 pushed main;
CI38433104767 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38433104767 . Downloaded
job115420095592 log verifies actual source/reader git outputs, Python3.10,
compileall and158 cases (138 pass/twenty original-file fixtures skipped).
All158 passed locally with original enabled; saved source/docs/test hashes
match. CI snapshots/job log and runtime oracle saved with evidence in
 data/furries/expression-strings/. This delivery update changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.


2026-10-13: Sol tick t_mv6x2lct1j4dr5, one bounded M0 numeric-addition token
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event-dump/13/schema13 annotates
exact four-byte0x0200 tokens with integer_operation add/32-bit/wrap-modulo2^32,
required numeric tag0 and explicit unknown nonnumeric semantics. Token storage,
literals, references and prior annotations remain unchanged. This exposes a
proven operation path without evaluating dynamic expressions, inferring actual
operand tags or folding constants; expression_evaluation remains false.
Short/extended recognized operators exit2 before any output/private report.
Existing optional detached fault reporter, atomic/symlink/immutable guards remain.

Primary proof: original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.
Evaluator0x42a42e selects table0x41b574+(code>>8)*2;0x0200 selects pointer
0x41b578 -> handler0x42a4b5. Its DL=0 branch adds EAX+ECX in32 bits.
Independent Unicorn2.1.4 runs actual handler and full evaluator for49 signed
boundary pairs plus512 seeded random pairs, verifying wrapping result, numeric
tag and stack; evaluator also checks the token cursor. All116 original addition
tokens are separately exercised between numeric literal probe operands through
the actual evaluator:1238 runs total. Original dynamic expressions themselves
are not evaluated, no runtime functions mocked; no standalone literal+literal
expression occurs in the original. String path/precedence/unary/other operators
remain unknown. No original instruction bytes or assets committed/published.
Evidence: agent state data/furries/expression-addition/.

Validation: forced compileall and all165 local tests pass with pinned
KlikBack6e178b9 and original enabled. Seven new cases cover exact-code isolation,
unknown/string contexts without result claims, short/extended shapes, all six
expression types/both roles/scopes, readable annotations, lossless reconstruction,
immutable bundle repeats, late-invalid refusal before all writes/reporting and
independent original source-word/external token walks for all116 operators.
Executed recognition0x0200->0x0600 control produces12 assertion failures/three
errors in seven executed cases; restored byte-exact and compileall-f before
final positives. Actual agent ./node_modules/.bin/tsc --noEmit passed.

Prior JSON fields match preceding cd009f0 after removing only operation
annotations/coverage/version. Prior text matches after removing new operation
annotations inside EXPRESSION JSON and changing banner/coverage sentence.
Previous643-file bundle refuses changed output without mutation and is preserved
before regeneration;640 other files remain identical. JSON/text/bundle CLIs
repeat identically; source project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Tested source delivery/CI result follows within this turn; no new schedule.
Combined furries-exporter-spec remains started/sol: actual expression/global/
opcode semantics, placement/arena geometry/spawns and observed behaviour remain
open. No playable engine/release/Windows/Deck/hardware claim or second slice.


Delivery: tested source221f1df9282c2fe2dec2f124d2606c25597d2929 pushed main;
CI38434690456 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38434690456 . Downloaded
job115425505322 log verifies actual source/reader checkout output, Python3.10,
compileall and165 tests (144 pass/21 original-file fixtures explicitly skipped).
All165 passed locally with original enabled; saved source/docs/test hashes
match. CI snapshots/job log and runtime oracle are saved with local evidence
in data/furries/expression-addition/. This delivery edit is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.


2026-10-13: Sol tick t_mv6xfimj1lweef, one bounded M0 minus-token slice.
Clean main, fetched origin, no open PRs/issues/in-flight work at start; direct
main follows repository convention. event-dump/14/schema14 annotates exact
four-byte0x0400 with numeric binary subtract/left-minus-right and operand-entry
prefix negate. Both specify32-bit/wrap-modulo2^32 and numeric tag0; nonnumeric
semantics remain unknown. Both annotations are retained without choosing the
actual context, validating expression grammar, folding constants or evaluating
dynamic expressions. Unsupported minus extents exit2 before any JSON/text/
bundle output or private report. Existing optional detached fault handler and
atomic/symlink/immutable guards remain unchanged.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e selects table0x41b574/pointer0x41b57c ->0x42a529, whose
EAX/ECX swap and subtraction establish left-minus-right. Dispatcher0x42a474
consumes prefix0x0400 and negates the loaded operand at0x42a4a9. Independent
Unicorn2.1.4 executes actual handler/evaluator on49 boundary+512 seeded pairs,
dispatcher/evaluator on7 boundary+512 seeded unary values, two mixed prefix/
binary streams per pair, and all63 original tokens between numeric probes.
All3345 executions verify wrapping results/numeric tags/stack; evaluator and
dispatcher also verify cursors. Reversed subtraction expectation fails on an
executed asymmetric pair. Initial unary oracle used stack low-word0; original
16-bit ADD SP,2 wrapped across64KiB, so valid-stack proof uses low-word0x1000.
This is isolated original instruction execution, not original dynamic
expressions, string/pointer behavior, arbitrary unary chains or gameplay.

Validation: forced compileall and all173 local tests pass with original and
pinned KlikBack6e178b9. Eight new cases cover both annotations/opaque contexts,
exact codes/extents, six expression types/both roles/scopes, readable text,
lossless source programs, immutable repeats and late-invalid refusal before
all output/reporting. Original test directly checks all63 source words/extents
and independently traverses external reader tokens. Recognition0x0400->0x0600
control produces12 intended assertion failures/four errors in eight executed
cases; restored byte-exact and compileall-f before positives. Actual agent
./node_modules/.bin/tsc --noEmit passed before commit. Existing version assertions
updated to14; addition original proof still checks all116 addition tokens.

Prior fields/addition/literal/reference/group annotations and text match cf00c21
after removing only new minus annotations/coverage/version/banner. Previous
643-file immutable bundle refuses replacement without mutation and is preserved
before regeneration;640 other files stay identical. JSON/text/bundle CLIs repeat
identically; project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
No original bytes/assets/exported metadata/private endpoint committed/published.
Evidence: agent state data/furries/expression-minus/; delivery/CI follows below.
Combined furries-exporter-spec remains started/sol: dynamic/global/opcode
semantics, placement/arenas/spawns and observation-backed behaviour remain open.
No second slice, schedule/continuation, release or hardware claim.

Delivery: tested source735188fc5e2f48267ad4c75b6090cf1f75c44535 pushed main;
CI38435915130 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38435915130 . Downloaded
job115429694825 log verifies actual source/reader checkout output, Python3.10,
compileall and173 cases (151 pass/22 original-file fixtures explicitly skipped).
All173 passed locally with original enabled; saved source/docs/test hashes match.
CI snapshots/job log and runtime oracle saved with evidence in agent state
 data/furries/expression-minus/. This delivery update is Markdown only; tested
source unchanged. No unfinished implementation/schedule/continuation; combined
exporter/spec remains started/sol, no release or second slice.


2026-10-13: Sol tick t_mv74xn6m0z9w5, one bounded M0 numeric multiplication
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event-dump/15/schema15 annotates
exact four-byte0x0600 with multiply/32-bit/wrap-modulo2^32 and required numeric
tag0; nonnumeric semantics/actual operand contexts remain unknown. No grammar,
precedence, constant folding, prefix multiplication or dynamic expression result
is claimed. Unsupported multiplication extents exit2 before JSON/text/bundle
writes or reporting. Existing optional detached FF_FAULT_REPORT_URL fault handler
and atomic/symlink/immutable output guards remain unchanged.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e selects table0x41b574/pointer0x41b580 ->0x42a52d. The handler
performs signed32 IMUL, returns low32 product bits and clears DX (upper16 EDX
may retain product bits). Independent Unicorn2.1.4 executes actual handler and
complete evaluator for49 signed-boundary pairs and512 seeded pairs, plus the
one original token between asymmetric numeric probes:1123 executions pass.
Results modulo2^32, low16 numeric tags and balanced stacks verified; evaluator
also verifies cursor. Original surrounding dynamic expressions/nonnumeric
inputs/gameplay are not executed; no dynamic functions mocked as evidence.
A deliberate addition expectation fails an executed product assertion.

Forced compileall and all181 local tests pass with original and pinned
KlikBack6e178b9. Eight new cases cover exact-code isolation, unsupported extents,
opaque contexts, signed boundary literals/mixed existing operations without
folding, all expression types/both roles/scopes, readable text, lossless programs,
late-invalid refusal before every output/report and immutable repeat bundles.
Independent source-program walks verify the sole original multiplication word
and extent. Recognition0x0600->0x0C00 control fails12 intended assertions/four
errors in eight executed cases; source restored byte-exact and compileall-f
forced before positives. Previous unknown-operator tests use still-opaque codes
now that0x0600 is supported; existing version assertions updated to15.
Actual agent ./node_modules/.bin/tsc --noEmit passes after locked dev dependencies
restored using npm ci --include=dev --ignore-scripts; agent source/lock unchanged.

Prior fields/literals/addition/minus/reference/group annotations and text match
831eb18 after removing only multiplication additions/coverage/version/banner.
Previous643-file immutable bundle refuses replacement without mutation, preserved
before regeneration;640 other files unchanged. JSON/text/bundle CLIs repeat
identically and input SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
No original instructions/assets/exported metadata/private endpoint committed or
published. Evidence: agent state data/furries/expression-multiplication/;
source delivery/CI follows within this turn. Combined furries-exporter-spec stays
started/sol: dynamic/global/opcode/placement/arenas/spawns/behaviour remain open.
No second slice, new schedule/continuation, release or hardware claim.

Delivery: tested source67dba7d9e27a8e78f3c761d4b93d5102e57c9460 pushed main;
CI38463884904 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38463884904 . Downloaded
job115525722753 log verifies actual source/reader checkout output, Python3.10,
compileall and181 tests (158 pass/23 original-file fixtures explicitly skipped).
All181 passed locally with original enabled; saved source/docs/test hashes match.
CI snapshots/job log and runtime oracle saved with evidence in agent state
 data/furries/expression-multiplication/. This delivery edit is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.

2026-10-13: Sol tick t_mv75aic72b4ka, one bounded M0 signed-division slice.
Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event-dump/16/schema16 annotates
exact four-byte0x0800 with signed32 divide/left-divided-by-right/toward-zero,
zero-divisor result0, x86 divide-error overflow and unknown exception recovery.
Numeric operand-tag0 only is proven; surrounding operand contexts/nonnumeric
semantics remain unknown. No grammar/precedence/folding/dynamic result is claimed.
Unsupported division extents exit2 before JSON/text/bundle writes or reporting;
existing optional detached fault reporter and atomic/symlink/immutable guards
remain unchanged. No private endpoint or original bytes/assets committed.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e selects table0x41b574/pointer0x41b584 ->0x42a535.
Handler swaps EAX/ECX, returns EAX0/DX0 on zero divisor, otherwise CDQ/IDIV ECX
at0x42a53b gives signed quotient followed by DX clear. INT32_MIN/-1 triggers
vector0 before return/tag clear; original OS/process recovery is not proven.
Independent Unicorn2.1.4 executes actual handler and complete evaluator on49
boundary+four rounding+512 seeded pairs; all15 original tokens additionally
run between numeric probes for both rounding signs, zero divisor and overflow.
1190 runs pass:1173 returned result/tag/balanced-stack checks,17 verified divide
errors at IDIV with fault operands/stack, and evaluator cursors in both outcomes.
Fresh CPU per execution avoids Unicorn retaining a pending exception and causing
a double fault on reuse. Initial trap-stack expectation was corrected from4 to6
bytes below entry: original evaluator also retains its two-byte outer BX.
A floor-division negative expectation fails on executed (-2147483648,2147483647).
No original surrounding dynamic expressions/nonnumeric inputs/gameplay mocked
or executed, and no OS exception recovery is claimed.

Forced compileall and all189 local tests pass with original/pinned KlikBack
6e178b9. Eight new cases cover isolation/opaque contexts, signed/zero/overflow
literal storage without evaluation, unsupported extents, all expression types/
both roles/scopes, readable annotations, lossless programs, immutable repeats,
late-invalid refusal before all outputs/reporting and independent original
source-word/external-reader traversal for all15 operator tokens.
Recognition0x0800->0x0E00 control fails12 intended assertions/four errors in
eight executed cases; restored byte-exact and compileall-f before positives.
Existing version expectations updated to16 and unknown-extent cases now use
still-opaque operators. Actual agent ./node_modules/.bin/tsc --noEmit passes.

Prior fields/literals/addition/minus/multiplication/references/groups/text match
b8e03d5 after stripping only division additions/coverage/version/banner.
Previous643-file immutable bundle refuses replacement without mutation and is
preserved before regeneration;640 other files remain identical. JSON/text/bundle
CLIs repeat identically; input SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/expression-division/; source delivery/CI follows
within this turn. Combined furries-exporter-spec stays started/sol: actual
expression/global/opcode/placement/arenas/spawns/behaviour remain open.
No second slice, schedule/continuation, release or hardware claim.

Delivery: tested sourced824a3a6b796d1aa25296c46d69b7267e47536cf pushed main;
CI38465183725 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38465183725 . Downloaded
job115529988945 log verifies actual source and reader checkout outputs,
Python3.10, compileall and189 tests (165 pass/24 original fixtures skipped).
All189 pass locally with original enabled; saved source/docs/test hashes match.
CI snapshots/job log and runtime oracle saved in agent state
 data/furries/expression-division/. This delivery update is Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec stays started/sol, no release or second slice.

2026-10-13: Sol tick t_mv75nd3s4dqmw, one bounded M0 signed-remainder
capability slice. Clean main, fetched origin, no open PRs/issues or in-flight
work at start; direct main follows repository convention. event-dump/17/schema17
annotates exact four-byte0x0A00 numeric remainder: signed32/quotient-toward-zero,
nonzero sign follows dividend, zero-divisor result is the left operand unchanged,
x86 divide-error overflow and unknown exception recovery. An independent original
project walk finds zero instances: runtime capability, no new gameplay claim.
No surrounding contexts, nonnumeric tags, grammar/precedence, constant folding or
dynamic results inferred. Unsupported extents fail exit2 before all outputs/reports.
Existing detached optional fault reporter and atomic/symlink/immutable guards
unchanged; no original bytes/assets/metadata/private endpoint committed/published.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e/table0x41b574 pointer0x41b588 -> handler0x42a547 swaps EAX/ECX,
CDQ/IDIV ECX at0x42a54d then MOV EAX,EDX returns signed remainder. Zero skips
IDIV/MOV, preserving dividend; INT32_MIN/-1 traps before result move/tag clear.
Independent Unicorn2.1.4 executes handler and complete evaluator for565 boundary/
rounding/seeded pairs:1130 runs,1128 checked returns/two vector0 overflows.
Result/low16 numeric tag/balanced stack and evaluator cursor verified; overflow
instruction/operands/trap stack verified. All seven boundary zero-divisors covered.
Fresh CPU per execution; OS recovery/dynamic/nonnumeric/gameplay not executed.
Python-modulo expectation fails (-2147483648,2147483647); zero-result expectation
fails (-2147483648,0), both on actual original instruction execution.

Forced compileall and all197 local tests pass with original/pinned KlikBack6e178b9.
Eight new cases cover isolation/opaque contexts, signed/zero/overflow literals
without evaluation, unsupported extents, all six expression types/both roles/
scopes, readable annotations, lossless programs, immutable repeats, late-invalid
refusal before every output/report and independent original absence proof.
Recognition0x0A00->0x0E00 control produces11 intended assertion failures/four
errors in eight executed cases (original-absence case passes); restored byte-exact
and compileall-f before final positives. Version assertions updated to17;
earlier unsupported-code cases now use still-opaque codes. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Prior JSON fields/annotations match b51201e after stripping only capability
coverage/version; original has no new token annotations. Prior text identical
apart from banner/coverage sentence. Previous643-file immutable bundle refuses
replacement without mutation and is preserved before regeneration;640 other
files identical. JSON/text/bundle CLIs repeat identically, source unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/expression-remainder/; delivery/CI follows
within this tick. Combined furries-exporter-spec stays started/sol: actual
expression/global/opcode/placement/arenas/spawns/observed behaviour remain open.
No second slice, new schedule/continuation, release or hardware claim.

Delivery: tested source65efebb277065e08a839a9b15378fadd41248d24 pushed main;
CI38466509299 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38466509299 . Downloaded
job115534577683 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and197 tests (172 pass/25 original-file fixtures skipped).
All197 pass locally with original enabled; saved source/docs/test hashes match.
CI snapshots/job log and runtime evidence saved in agent state
 data/furries/expression-remainder/. This delivery edit changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec stays started/sol, no release or second slice.

2026-10-13: Sol tick t_mv76091x6nxz4, one bounded M0 expression-control
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event-dump/18/schema18 annotates
exact four-byte0xFFFF recursive operands and0xFEFF/0xFDFF evaluator stops,
including the unconsumed inner cursor and outer dispatcher consumption. No
pairing, function argument role, grammar validation or dynamic result guessed.
Placement fields were inspected but have no independent field evidence yet;
no placement change made. Unsupported control extents exit2 before all outputs
or fault reporting; existing detached optional private reporter unchanged.
No original instructions/content/assets/metadata/private endpoint committed.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
dispatch0x42a474/type-1 table0x41b2b8 entry0x41b2b4 -> recursive handler0x42a4ac;
ADD EDI,4 then evaluator0x42a42e. Stops checked at0x42a449/0x42a450 remain
at EDI; dispatcher consumes returned cursor's extent. Independent Unicorn2.1.4
executes real handler/dispatcher/evaluator on177 boundary/seeded pairs with both
stops, nested arithmetic/prefix signs, depths1/2/4/8/16/32 and numeric/string
tags. All1906 runs verify result/pointer/low16 tag/cursor/return/balanced stack.
Poison tokens after stops do not execute. Grouped(7+3)*5 returns50 versus
ungrouped7+3*5 returns22; this is not a complete precedence/grammar spec.
An independent original source walk verifies all126 tokens (4 recursive,
105FEFF/17FDFF stops), each run between independent probes. No original dynamic
operands/global gameplay/function calls mocked or executed. Unmatched recursion
runtime safety/zero-terminator length reads remain unknown, storage stays lossless.

Forced compileall and all205 local tests pass with original/pinned KlikBack6e178b9.
Eight new cases cover source words/extents and lossless programs, nested/unbalanced
storage, unknown neighbours, runtime-stop versus storage-terminator scanning,
both roles/all six expression types/scopes, readable annotations, immutable
repeats and late-invalid refusal before all outputs/reporting. FFFF->FCFF
recognition control fails12 assertions/three errors in8 executed cases; restored
byte-exact and compileall-f before final positives. Grouped-result22 expectation
fails actual runtime result50; consumed-stop cursor expectation fails a direct
evaluator probe. Actual agent ./node_modules/.bin/tsc --noEmit passes.

Prior fields/annotations and text match3e7d8c9 after removing only control
additions/coverage/version/banner. Previous643-file immutable bundle refuses
replacement without mutation and is preserved before regeneration;640 other
files unchanged. JSON/text/bundle CLIs repeat identically; original unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/expression-control/; delivery/CI follows
within this tick. Combined furries-exporter-spec stays started/sol: actual
expression/global/opcode/placement/arenas/spawns/observed behaviour remain open.
No second slice, schedule/continuation, release or hardware claim.

Delivery: tested sourcec5c8239852023faf1c94945f3b8f79810a1a8123 pushed main;
CI38468144884 completed/success on that exact source:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38468144884 . Downloaded
job115540060476 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and205 tests (179 pass/26 original-file fixtures skipped).
All205 pass locally with original enabled; saved source/docs/test hashes match.
CI snapshots/job log and runtime evidence saved in agent state
 data/furries/expression-control/. This delivery edit changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec stays started/sol, no release or second slice.

2026-10-13: Sol tick t_mv76d2tv80u8u, one bounded M0 closed integer-expression
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. event-dump/19/schema19 adds
`constant_integer_evaluation` to expression storage. New tools/integer_constants.py
conservatively evaluates complete ungrouped integer-literal streams with the five
supported numeric binary operators and at most one prefix minus per operand.
Unsupported tokens/shapes refuse the whole stream before arithmetic; no dynamic,
string, recursive/stop-token or grouped evaluation is invented. Raw prefix/suffix,
tokens/annotations/references and unknown parameter/opcode meanings stay preserved.
General expression/parameter/behaviour coverage remains false; new bounded
constant_integer_expressions coverage is true. CPU divide errors are research
results with pending operator ID and unknown OS recovery, not exporter crashes;
existing detached optional private fault handler remains unchanged.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e compares raw signed16 operator codes at0x42a457 and uses
table0x41b574. Each code has distinct priority (remainder > divide > multiply >
subtract > add), equal codes associate left; prefix minus wraps before binary
arithmetic. In particular20*7/3 gives40, not46. Every intermediate wraps32 bits;
signed divide/remainder truncate toward zero, zero divisors retain prior proven
behavior and INT32_MIN/-1 faults. Independent Unicorn2.1.4 executes unmodified
original evaluator/dispatcher/operators on all25 ordered operator pairs ×six
triples ×eight prefix-sign masks,1024 seeded streams (up to16 operands), four
priority/association probes and all3490 eligible original expression byte streams.
All5718 runs pass:5667 checked normal results/numeric tags/cursors/balanced stacks,
51 vector0 faults with matching IDIV address, fault operands and retained return
address. All3490 original eligible expressions are SINGLE LITERALS; compound
capability is synthetic evidence, not new compound gameplay observation.
The other378 original expressions remain unresolved. No OS exception recovery,
dynamic/nonnumeric/grouped/gameplay execution or mocks claimed. A conventional
arithmetic46 expectation fails on actual original result40.

Forced compileall and all215 local tests pass with original/pinned KlikBack6e178b9.
Ten new cases cover raw-code priority/equal-code association, signed/prefix
boundaries, wrapping intermediates, rounding/zero/overflow and pending fault
identity, complete-stream refusal, unknown/unbalanced forms, opaque tails, long
iterative streams, all six expression types/both roles/scopes, readable results,
lossless programs, immutable repeats, late malformed extents before every output
or fault report, and independently classified original source words/results.
Reversed >= to <= operator-reduction control fails seven intended assertions in
ten executed cases; restored byte-exact and compileall-f before final positives.
Existing version assertions become19; literal-text assertion includes the new
separate whole-expression result. Actual agent ./node_modules/.bin/tsc --noEmit
passes before commit.

Prior JSON fields/annotations and text match971d55c after stripping only the new
constant_integer_evaluation/coverage/version/banner additions. Previous643-file
immutable bundle refuses replacement without mutation and is preserved before
regeneration;640 other files remain identical. JSON/text/bundle CLIs repeat
identically; input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
No original code/instructions/assets/exported metadata/private endpoint committed
or published. Evidence: agent state data/furries/expression-constants/;
source delivery/CI follows within this tick. Combined furries-exporter-spec stays
started/sol: dynamic/global/opcode/placement/arenas/spawns/observed behaviour open.
No second slice, new schedule/continuation, release or hardware claim.

Fixture follow-up: the new immutable-repeat test now writes its synthetic bundle
under this checkout's ignored build/ rather than shared /tmp. All10 affected
cases pass with the original enabled and forced compileall; actual agent tsc
passes again. Evaluator/exporter/docs and all other tested files are unchanged
from13a22cf; final source delivery/CI below covers this fixture revision too.

Delivery: final tested source3b8c6c56e9d378855fe1721d5684980dd336500a pushed main;
CI38469763055 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38469763055 . Downloaded
job115545502827 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and215 tests (188 pass/27 original fixtures skipped).
All215 passed locally before the scratch-directory-only test change; all10
new affected cases passed again afterwards with original enabled. Exporter/
evaluator/docs hashes unchanged across that fixture change; final saved hashes
match CI-tested source. Initial13a22cf CI38469522395/job115544659852 also green
with actual source/reader/test outputs verified. CI snapshots/logs, prior bundle
compatibility and independent runtime proof saved in agent state
 data/furries/expression-constants/. This delivery edit changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec remains started/sol, no release or second slice.

2026-10-13: Sol tick t_mv772t0oank5s, one bounded M0 closed recursive
integer-expression slice. Clean main, fetched origin, no open PRs/issues or
in-flight work at start; direct main follows repository convention. event-dump/20
schema20 extends constant_integer_evaluation to closed FFFF recursive operands
with either FEFF/FDFF stop, nested/mixed stops and single prefix signs applied
on return. Iterative complete-stream validation precedes arithmetic; no Python
recursion limit, implicit zero-stop closure, dynamic/string/function evaluation
or general delimiter grammar guessed. Unsupported shapes/results and CPU faults
remain research output; malformed extents exit2 before all writes/reports.
Existing detached optional private exporter fault handler unchanged. No original
instructions/content/assets/exported metadata/private endpoint committed/published.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
evaluator0x42a42e/dispatcher0x42a474/recursive handler0x42a4ac independently
executed unmodified with Unicorn2.1.4. Both stops, depths1..64, all25 ordered
operator pairs/signs/boundaries/zero, competing faults and1024 seeded nested
streams:7754 runs pass (7604 normal result/numeric tag/cursor/balanced-stack
checks;150 vector0 faults with IDIV address/operands/EXACT pending token ID and
retained return address). Instruction hooks observe operator pushes/entries
without altering execution. Reductions happen before reading a subsequent
operand when raw-code priority requires it: pre-evaluating all child groups
would misidentify an earlier outer fault. Grouped(7+3)*5 returns50; a deliberate
ungrouped22 runtime expectation fails after actual original instruction execution.
All3490 eligible original byte streams still SINGLE LITERALS;378 remain unknown.
All4 recursive/105FEFF/17FDFF original words independently traversed in streams
containing unknown dynamic/function tokens. No new original compound result,
OS recovery/nonnumeric/gameplay/hardware claim.

Forced compileall and all224 local tests pass with original/pinned KlikBack6e178b9.
Nine new cases cover stop/priority/prefix/numeric boundaries, competing fault
identity, complete-stream refusal,4096 iterative nested operands/opaque tails,
all six expression types/both roles/scopes, readable/lossless output, immutable
bundle repeats, late malformed controls before JSON/text/bundle/reporting and
independent original traversal. Omitting recursive return prefix negation causes
three intended failures in nine executed cases; restored byte-exact/compileall-f
before all224 final positives. Coverage-banner follow-up changes only one output
sentence; nine affected cases pass again. Actual agent tsc passes before commit.
Previous versions updated to20; old control-only unsupported tests now assert
unsupported_shape rather than unsupported_tokens, with full shape cases added.

Prior fields/raw tokens/annotations match31e9fb3 except evaluation token_ids in
103 unsupported original streams now omit the newly supported control words;
remaining unknown tokens prevent results. All previous statuses/values unchanged;
text only changes those IDs/version/coverage sentence. Previous643-file immutable
bundle refuses replacement without mutation and is preserved before regeneration;
640 other files identical. JSON/text/bundle CLIs repeat identically/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/expression-recursive/; source delivery/CI follows
within this turn. Combined exporter/spec stays started/sol: placement/arenas/
spawns/dynamic/global/opcode/observed behaviour remain open. No second slice,
schedule/continuation or release.

Delivery: tested source94bb4d47b8fe26e204bf46ffabaf6bb11dbbcb11 pushed main;
CI38471902797 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38471902797 . Downloaded
job115552822284 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and224 tests (196 pass/28 original fixtures skipped).
All224 passed locally after restoration with original enabled; nine new affected
cases passed again after the coverage sentence follow-up. Saved tested file hashes
match the CI-tested source. Evidence/CI snapshots/job log in agent state
 data/furries/expression-recursive/. This delivery edit changes Markdown only;
tested source unchanged. No unfinished implementation/schedule/continuation;
combined exporter/spec stays started/sol, no release or second slice.

2026-10-13: Sol tick t_mv77fo0qc1dn3, one bounded M0 placement/local-object
probe slice. Clean main, fetched origin, no open PRs/issues or in-flight work at
start; direct main follows repo convention. frame-layout/2/schema2 adds an
explicit object_slot_probe per stored placement record: u16 at record0 looked
up as an index in every same-frame object-definition list. Candidates retain
actual definition block identities, names/types/flags/global/deleted state;
missing/deleted/ambiguous cases remain explicit. No global-body fallback, event
reference encodings, pointer sentinels or expected object types are borrowed.
Every probe says runtime_resolution=false/stored_word_local_slot_equality.
This is a storage correlation for investigating arena object references, not a
decoded runtime field or verified geometry, spawns, ordering/collision/behaviour.
General placement/arena/spawn/behaviour coverage remains false. Existing
detached optional private fault handler is unchanged; malformed placements
still exit2 before either standalone/bundle writes or fault reports.

Independent original source-span reads and pinned-reader object_definitions
traversal verify all7,968 records across12 placement blocks: each first word has
exactly one live same-frame slot candidate. Global-flagged local headers stay
local candidates, not selected application-global payloads. All record/slot/
header fields and bytes compare exactly with c17af61 after removing only the
new annotation/coverage/version. Original unchanged and repeat CLIs identical:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Previous643-file immutable bundle refuses replacement without mutation and is
preserved before regeneration;641 files unchanged, only frame-layout.json and
manifest.json differ. No original code/assets/exported metadata/private endpoint
committed or published; no editor/runtime/hardware execution claimed.

Forced compileall and all232 local tests pass with original/pinned KlikBack
6e178b9 enabled. Eight new cases cover source spans/independent candidates,
same-frame scope/actual block IDs/repeated definitions, all u16 boundaries,
missing/deleted/ambiguous slots, no global fallback, reversed pointers/aliases/
gaps, empty/repeated blocks/escaped names, immutable bundles and late malformed
refusal before all outputs/reporting. Slot-index+1 negative control causes six
intended assertion failures/one missing-candidate error in8 executed cases;
restored byte-exact and compileall-f before final positives. Actual agent
./node_modules/.bin/tsc --noEmit passes. Evidence in agent state
data/furries/placement-object-probes/; source delivery/CI follows within this
tick. Combined furries-exporter-spec stays started/sol: record coordinates,
arena geometry/spawns/dynamic/global/opcode/observed behaviour remain open.
No second slice, new schedule/continuation or release.

Delivery: tested source99ce9472cd6dc82f2d34e195a765113145f8628d pushed main;
CI38473067395 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38473067395 . Downloaded
job115556823693 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and232 tests (203 pass/29 original fixtures skipped).
All232 passed locally with original enabled after negative-control restoration.
Saved source/docs/test hashes match the CI-tested revision. Evidence/CI snapshots/
job log in agent state data/furries/placement-object-probes/. This delivery edit
changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, placement/arena/spawn/observed behaviour semantics still open.

2026-10-13: Sol tick t_mv77sinteaz21, one bounded M0 event position
coordinate-input slice. Clean main, fetched origin, no open PRs/issues or
in-flight work at start; direct main follows repo convention. event-dump/21
schema21 adds position_coordinate_storage beside unchanged position references:
flags u16 at payload2, X/Y unsigned bits and signed16 views at4/6, source offsets
and explicit unresolved runtime positions. Only established source FFFE/FFFF
sentinels get absolute_xy; other encodings/locals/globals remain context_dependent.
All original1263 remain context dependent; no actual spawn/global/selected-object
result inferred. Type21 synthetic storage evidence only; no complete flag,
noncartesian/hotspot/direction/clipping/opcode/gameplay semantics claimed.
Existing optional detached private exporter fault handler unchanged; malformed
supported shapes exit2 before every output or fault report. No original code,
assets/exported metadata/private endpoint committed/published.

Unmodified original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
position helper0x42a2a6/direct word reads0x42a2d8 and cartesian additions0x42a393
independently executed with Unicorn2.1.4, including authentic cached selector
0x426c0f/0x426e2a (no patched instructions/imports/selector stubs). Seven signed
boundaries/both axes/two sentinels/six flags/three selected origins/512 seeded
probes and every original parameter's source coordinate words in TWO SYNTHETIC
contexts:4286 executions pass (2364 absolute,1922 relative cartesian).
Coordinate bits/DX/carry/return/stack/restored ESI+EDI/input unchanged checked;
wrong positive7 expectation fails on actual negative7 bits. Original references
and flags are deliberately changed for context probes, so these are arithmetic
capabilities, not actual original event/selection/position results.
Independent direct source-span reads and pinned remapper preserve all1263 words:
1150 type9,110 type18,3 type16; flags10:570/2:30/6:80/8:583. Original helper's
image-dependent hotspot/other modes and source-slot→runtime remapping remain open.

Eight new cases and all240 local tests pass with original/pinned KlikBack6e178b9.
Signed/raw boundaries and asymmetric axes, opaque flags/reference encodings,
all four types/both roles/scopes, original span/remapper agreement, readable and
lossless programs, immutable repeats and late short parameters before JSON/text/
bundle/reporting covered. X signed-offset4→5 control fails4 intended assertions
in8 executed cases; source restored byte-exact and compileall-f before final
all240 positives. Actual agent ./node_modules/.bin/tsc --noEmit passes before
commit. Prior JSON fields/references/evaluation/groups and text match202be03
when removing only coordinate additions/version/coverage. Previous643-file bundle
refuses replacement without mutation and is preserved before regeneration;
640 other files identical. JSON/text/bundle repeats identical/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/position-coordinates/; source delivery/CI
follows within this tick. Combined furries-exporter-spec stays started/sol:
placement/arena geometry/spawns/global/opcode/actual selection/observed behaviour
remain open. No second slice, new schedule/continuation, release or hardware claim.

Delivery: tested source5ee1a664d8b823c9d4ba8c088cdef6e57c2230b4 pushed main;
CI38474522649 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38474522649 . Downloaded
job115561819566 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and240 tests (210 pass/30 original fixtures skipped).
All240 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/position-coordinates/. This delivery
edit changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual selection/arena geometry/spawn/observed behaviour still open.

2026-10-13: Sol tick t_mv785f25g83hu, one bounded M0 placement creation
coordinate-input slice. Clean main, fetched origin, no open PRs/issues or
in-flight work at start; direct main follows repository convention. frame-layout/3
schema3 adds coordinate_inputs beside unchanged raw records/object-slot probes:
X at record2, Y at4, raw-u16 and reversible signed-i16 views. Each axis uses
its record word only if the corresponding creator argument is0x8000; the marker
is not a record sentinel. Every annotation runtime_resolution=false; record
meaning remains unknown. No final live position/spawn/collision/arena semantics
inferred. Context-free storage decoder unchanged. Existing detached optional
private fault reporter unchanged; malformed input still exit2 before writes/
reporting. No original instructions/assets/content/exported metadata/endpoint
committed or published.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
creator0x420ac1 coordinate branch0x420c28..0x420c54 independently executed
unmodified in Unicorn2.1.4, copying record2/4 or explicit override words to
local/object coordinate words. Real initial caller0x40b73b..0x420ac1 executes
its actual0x406020 lookup and supplies0xffff8000 for both coordinate arguments.
Seven signed boundaries/both axes/four override paths/512 seeded records and
all7968 original record byte spans:17718 executions pass (9189 coordinate paths,
8529 caller paths). Result bits/local copies/caller arguments/untouched input
and other object bytes/stack/register preservation checked; wrong positive7
expectation fails after original negative7 execution. Protected original's12
placement blocks match decompiled source bytes exactly. These are PARTIAL
instruction paths in synthetic state, not full original allocation/filtering/
definition selection/object or movement initialization/drawing/gameplay.
The creator copies16 bits; signed view is two's-complement representation.
Full runtime positions, player-spawn selection and arena collision still open.

Forced compileall and all248 local tests pass with original/pinned KlikBack
6e178b9 enabled. Eight new cases cover signed/raw/asymmetric boundaries, opaque
neighbours, argument marker versus stored0x8000, aliases/reversed pointers/gaps,
empty/repeated blocks/both frame headers, existing probes/signed JSON/immutable
bundle repeats, independently walked original spans/lossless reconstruction and
late short record before standalone/bundle output/reporting. X word-offset2->3
control fails53 intended assertions (including49 boundary subtests) in8 executed
cases; restored byte-exact and compileall-f before all248 positives. Existing
component-version expectations updated to3. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Prior raw fields/object-slot probes/headers/slots match eb4a952 after stripping
only new coordinate_inputs/coverage/version fields. Previous643-file immutable
bundle refuses replacement without mutation and is preserved before regeneration;
641 other files identical, only frame-layout.json/manifest.json change. Both
standalone/bundle CLIs repeat identically/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/placement-coordinates/; source delivery/CI
follows within this tick. Combined exporter/spec stays started/sol: arena
geometry/spawns/actual creation/selection/global/opcode/observed behaviour open.
No second slice, new schedule/continuation, release or hardware claim.

Delivery: tested sourcef8a4ea9f0d22769b607a8d91b61ddc4c200a4ac8 pushed main;
CI38475568447 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38475568447 . Downloaded
job115565275863 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and248 tests (217 pass/31 original fixtures skipped).
All248 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/placement-coordinates/. This delivery
edit changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, full creation/selection/arena geometry/spawn/observed behaviour open.

2026-10-13: Sol tick t_mv78i9bbizfps, one bounded M0 placement creation-type
input slice. Clean main/fetched origin, no open PRs/issues or in-flight work;
direct main follows repository convention. frame-layout/4/schema4 adds
creation_type_input: raw-u16 at record6, masked low-byte type and opaque high
byte, plus every existing same-frame header candidate's type comparison. Missing,
deleted/mismatching/ambiguous candidates stay explicit, no global fallback or
sentinel rules borrowed. Raw records/probes/coordinates and context-free decoder
unchanged; runtime_resolution=false throughout. Existing optional detached
private fault reporter unchanged; malformed input still exit2 before writes/
reporting. No original code/instructions/content/assets/exported metadata/private
endpoint committed or published.

Unmodified original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
creator0x420af3 reads record6, masks CX with0xff at0x420af7, then calls actual
allocation-dispatch helper0x420984. Independent Unicorn2.1.4 runs all65536 words,
224 missing extension entries,512 seeded records/all7968 originals plus wrong
full-word257 expectation:74241 executions pass (10735 zero-entry returns,
5707 built-in call entries,57799 extension call entries). Actual masked selector,
mixed-width stack arguments, real helper target/zero result/stack and untouched
records checked. Observational hooks only; original built-in pointers retained,
extension callback addresses/body offsets supplied as synthetic DATA inputs.
No callback code/stub/import replacement or allocation callback execution.
Full creator/object initialization/definition lookup/gameplay remain unproven.

Independent source spans/pinned-reader definitions confirm all7968 low bytes
match exactly one live same-frame header;1722 high bytes nonzero (still opaque).
Protected/decompiled placement blocks equal. Built-in table0/1 entries are zero:
5090 original records yield no helper callback in synthetic creator contexts;
this does NOT imply backdrop absence, since other rendering/filtering paths
were not executed. Actual arena geometry/spawn/global/body selection remain open.

Eight new tests/all256 local tests pass with original/pinned KlikBack6e178b9.
Coverage includes all low bytes/seven high-byte patterns, opaque neighbours,
all candidate shapes/scopes, aliases/gaps/reversed pointers/both frame headers,
empty/repeated blocks, original word/header traversal, standalone/bundle repeats
and late malformed refusal before output/reporting. Low-byte mask0xff->0xffff
control fails7 intended assertions in8 executed cases; restored byte-exact and
forced compileall-f before all256 final positives. First full run caught three
accidental fixture slot edits during version-assertion updates; original slots
restored and caches rebuilt before accepting final positives. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Prior document fields match807a114 after stripping only the new annotation/
coverage/version. Previous643-file immutable bundle refuses replacement without
mutation and is preserved before regeneration;641 other files identical, only
frame-layout.json/manifest.json differ. Both standalone/bundle CLI repeats
identical/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/placement-types/; source delivery/CI follows
within this tick. Combined exporter/spec stays started/sol: arena geometry/spawns,
actual allocation/selection/global/opcode/observed behaviour remain open.
No second slice, new schedule/continuation/release or hardware claim.

Delivery: tested sourceca310e9025af38ade97b368a19b0db99ed457a87 pushed main;
CI38476678023 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38476678023 . Downloaded
job115568953513 log verifies actual source and pinned-reader checkout outputs,
Python3.10, compileall and256 tests (224 pass/32 original fixtures skipped).
All256 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/placement-types/. This delivery edit
changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, full creation/selection/arena geometry/spawn/observed behaviour open.

2026-10-14: Sol tick t_mv7g07dwkqfpm, one bounded M0 frame dimension-input
slice. Clean main, fetched origin, no open PRs/issues or in-flight work at start;
direct main follows repository convention. frame-layout/5/schema5 adds per-frame
`dimension_inputs`: width at header4/height6, raw-u16 and signed-i16 views, both
0x78/0xB8 extents. Zero/negative/sentinel-looking bits preserved, other header
words remain opaque; raw placement fields/probes/type/coordinate inputs unchanged.
Every annotation runtime_resolution=false; arena collision/spawn/window/gameplay
semantics remain open. Existing optional detached private fault reporter unchanged;
invalid inputs fail before standalone/bundle writes/reporting. No original code,
assets/exports/proof data/private endpoint committed or published.

Original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
loader0x401e4f prepares 0x78/0xb8 read into0x41d662 (stopped before import);
size/centering0x404486..0x4044ef and clipping0x40567f paths execute unmodified
in Unicorn2.1.4. Seven word boundaries/both axes/extents,512 seeded header/app
pairs, both application-size selection contexts and13 original dimension pairs:
1249 cases/2496 instruction-path executions pass. Signed loads, independent size
selection/minima/centering/clipping branch, stack/registers and unchanged effective
header bytes checked; unsigned65529 expectation fails actual signed-negative7.
Header data/selection bit deliberately varied in synthetic contexts; file-read
import/full frame loading/drawing/gameplay never executed or stubbed. All13
protected/decompiled dimension byte pairs equal:350x150 then12*800x600; dimensions
alone do not identify playable arenas or collision boundaries.

Eight new cases and all264 local tests pass with original/pinned KlikBack6e178b9.
Signed/raw/asymmetric boundaries, opaque neighbours/both extents, zero/negative
preservation, unsupported header shapes, empty/repeated placement blocks/prior
annotations, original absolute source reads, immutable bundles/repeats and late
malformed placement/decoder extent before outputs/reporting covered. Width-offset
4->5 control fails101 intended assertions (98 boundary subtests) in8 executed
cases; restored byte-exact and compileall-f before all264 final positives.
Actual agent ./node_modules/.bin/tsc --noEmit passes before commit.

Prior document matches c250755 after removing only dimension_inputs/coverage/
version. Previous643-file immutable bundle refuses replacement without mutation
and is preserved before regeneration;641 files unchanged, only frame-layout.json/
manifest.json differ. Standalone/bundle CLIs repeat identically/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/frame-dimensions/; source delivery/CI follows
within this tick. Combined exporter/spec stays started/sol: arena geometry/spawns,
full creation/selection/global/opcode/observed behaviour remain open. No second
slice, new schedule/continuation/release or hardware claim.

Delivery: tested sourcea1159d5806e07701ee2bafbc79da5f9ae392489c pushed main;
CI38497590468 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38497590468 . Downloaded
job115636813375 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and264 tests (231 pass/33 local-original skips).
All264 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/frame-dimensions/. This delivery edit
changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, arena collision/spawns/full creation/selection/observed behaviour open.

2026-10-14: Sol tick t_mv7gcz9zmm8iv, one bounded M0 quick-backdrop
header dimension-input slice. Clean main, fetched origin, no open PRs/issues
or unfinished work at start; direct main follows repository convention.
backdrop-dump/2 schema2 adds nullable quick_backdrop_dimension_inputs: type0
width at header34/height36, raw-u16 and signed-i16 views, placement destinations
26/28. Ordinary type1 stays null: its bounds use image metadata, not those
header words. All58 original quick headers/352 ordinary headers checked against
independently walked absolute source spans. Raw headers/artwork/image-bank
candidates unchanged; global-flagged local headers remain stored local inputs,
not a selected global runtime body. Every annotation runtime_resolution=false.
Existing optional detached private fault reporting unchanged; malformed inputs
exit2 before standalone/bundle output/reporting. No original code/instructions,
assets/exports/proof data or private endpoint committed/published.

Unmodified original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
complete helper0x40f250 copies quick header34/36 to placement26/28, overwriting
old placement dimensions. Rectangle branch0x405886..0x4058c8 sign-extends and
adds origins; fill prologue0x4054b0..0x4054e3 sign-extends, adds origins minus1
and applies signed clip minima. Independent Unicorn2.1.4 executes2310 paths:
1070 complete helper calls,620 of each rectangle path; seven word boundaries,
ordinary/non-backdrop branches,512 seeded header/origin/clip contexts and all410
original headers. Destination/untouched bytes, stack/helper-preserved registers
checked; unsigned65529 expectation fails actual signed-negative7. Headers and
records are supplied DATA, with deliberately conflicting old dimensions; no
instruction/import/callback replacement. Loader0x402638 calls the helper but
full loading/global selection/culling/drawing/gameplay are not executed/proven.
Collision, actual arena bounds/spawns and ordinary image metadata remain open.

Eight new cases/all272 local tests pass with original/pinned KlikBack6e178b9;
compileall-f forced. Coverage: all supported fills/asymmetric signed boundaries,
zero/negative/sentinel-looking bits, opaque ordinary words/neighbours, differing
local/global headers/repeated/empty banks/lists, standalone/bundle immutable
repeats, original absolute source spans and late bad fills/truncated definitions
before either output/reporting. Width-offset34->35 negative control fails199
intended assertions in8 executed cases; source restored byte-exact and forced
compileall-f before all272 final positives. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Prior document equals3d858c7 after stripping only new dimensions/coverage/version.
Previous643-file immutable bundle refuses replacement without mutation and is
preserved before regeneration;641 other files identical, only backdrops.json/
manifest.json differ. Standalone/bundle CLIs repeat identically/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/backdrop-dimensions/; source delivery/CI follows
within this tick. Combined exporter/spec stays started/sol: arena geometry/spawns,
global/actual creation/selection/opcode/observed behaviour remain open.
No second slice, new schedule/continuation/release or hardware claim.

Delivery: tested source2ad089bc5d84decfad9e95f7a9b612931eb0d2bb pushed main;
CI38498380080 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38498380080 . Downloaded
job115639262052 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and272 tests (238 pass/34 local-original skips).
All272 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/backdrop-dimensions/. This delivery
edit changes Markdown only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, full header selection/arena collision/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7gpvrgqf0bt, one bounded M0 ordinary-backdrop
image-bank dimension-candidate slice. Clean main, fetched origin, no open PRs/
issues or in-flight work at start; direct main follows repository convention.
backdrop-dump/3 schema3 adds ordinary_backdrop_image_candidates: header image
word54 joins application image BANK SLOTS, preserving every matching segment,
record offset/extent/hash/raw24-byte header and width/height words10/12.
Single/multiple candidate states explicit; all runtime_resolution=false. Quick
backdrops have null ordinary candidates and retain their existing dimensions.
Global-flagged local headers keep their stored handles; conflicting repeated
banks have no chosen winner. Context-free decode_header remains unchanged.
No signed live-dimension/origin/hotspot/collision/runtime selection semantics
inferred. This is stored metadata corroborated by PNG output, not a new execution
proof of the original imported image-metadata function or actual arena geometry.

Referenced ordinary metadata must have24 header bytes and matching payload
length at6. Zero/large dimension words and opaque mode/flags stay intact; no
pixel decoder/limit is borrowed into the header-only view. Unused/mosaic image
metadata is outside this annotation; complete research bundles still validate
all supported pixels before writes. Existing optional detached private reporter
unchanged; malformed metadata exits2 before standalone/bundle output/reporting.
No original content/assets/instructions/exports/private endpoint committed.

All352 original ordinary references agree with independently read absolute
source-bank spans, record hashes/header/size words and decoded PNG IHDR/CRC/
scanline readback; all58 quick headers have null ordinary candidates. Eight new
cases cover raw asymmetric boundaries/header-only opaque pixel modes, bank-slot
identity versus internal image words, differing local/global handles/conflicting
repeated banks, quick/unused metadata scope, immutable standalone/bundle repeats,
and late short/length-mismatched referenced metadata before outputs/reporting.
Synthetic backdrop bank fixtures now carry valid own image headers instead of
one-byte placeholders; earlier source-word/artwork test intent preserved.
Initial slice tests caught a local variable shadowing the definition-list input;
corrected before positive validation, and malformed-path tests now also assert
the intended image-metadata error was reached.

Forced compileall and all280 local tests pass with pinned KlikBack6e178b9 and
original enabled. Image width-offset10->11 control fails5 intended assertions
in8 executed cases; source restored byte-exact and compileall-f forced before
final full positives. Actual agent ./node_modules/.bin/tsc --noEmit passes before
commit. Prior raw/artwork/quick-dimension fields match8bfd5d8 after stripping
only additions/coverage/version. Previous643-file immutable bundle refuses
replacement without mutation and is preserved before regeneration;641 other
files identical, only backdrops.json/manifest.json change. Standalone/bundle
CLIs repeat identically, source input unchanged SHA256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Source delivery/CI follows within this tick.
Evidence: agent state data/furries/backdrop-image-dimensions/. Combined
furries-exporter-spec stays started/sol: actual header/bank selection, arena
geometry/spawns/global/opcode/observed behaviour remain open. No second slice,
new schedule/continuation, release or hardware claim.

Delivery: tested source88ed676b49f6acca49ede986a13e6e625ba0bc17 pushed main;
CI38499341870 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38499341870 . Downloaded
job115642314933 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and280 tests (245 pass/35 local-original skips).
All280 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/backdrop-image-dimensions/. This
delivery edit changes Markdown only; tested source unchanged. No unfinished
implementation, continuation/new schedule/release/second slice; combined
exporter/spec remains started/sol, actual image/header selection/arena collision/
spawns/opcode/observed behaviour still open.

2026-10-14: Sol tick t_mv7h2pznsp0tc, one bounded M0 complete backdrop
header-to-placement refresh-input slice. Clean main/fetched origin, no open
PRs/issues or in-flight work at start; direct main follows repo convention.
backdrop-dump/4 schema4 adds placement_refresh_inputs: ordered conditional writes
from the supplied header, source/destination offsets/extents/raw/mask/written
unsigned values, low-byte dispatch and runtime_resolution=false. Common dword50
copies to placement12; type word42 masked0x0fff copies to6; quick-only colors24/28,
full fill WORD32 and dimensions34/36 copy to16/20/24/26/28; both backdrop kinds
copy image word54 to8, even if the quick solid/gradient artwork leaves it unused.
High type bits/common dword/high fill byte stay opaque. No actual header/global
selection, effective placement, collision, arena geometry/spawn/behaviour claim.
Previous header/artwork/quick dimension/ordinary-image candidates unchanged;
non-backdrop/deleted objects remain null. Existing detached optional private
fault reporter unchanged; invalid fill/shape exits2 before output/reporting.
No original instructions/content/assets/exports/private endpoint committed.

Unmodified original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
complete refresh helper0x40f250 executes through return in Unicorn2.1.4 for all
65536 type words,512 seeded supported headers,all410 original backdrop headers
and one incorrect low-byte-only expectation:66459 executions. Every record byte,
unchanged header/instructions, return stack and callee-preserved registers checked.
Applying exported input writes to synthetic prior records agrees with all1435
supported helper executions. Unsupported non-backdrop dispatch branches tested
only by the oracle, not newly exported. Synthetic DATA deliberately conflicts
with stored header inputs; no instruction/import/callback replacements or full
loading/header-selection/drawing/gameplay execution. Low-byte-only expected1
fails actual0xa01 from supplied type0xfa01. All410 original headers independently
checked against absolute source spans, including raw opaque fields.

Eight new cases and all288 local tests pass with original/pinned KlikBack6e178b9;
forced compileall-f. Coverage includes every high-byte pattern, ordered writes,
opaque neighbours, full quick-fill word, unused image copy, ordinary write scope,
differing local/global headers/repeated banks/empty lists, immutable standalone/
bundle repeats, original source spans and late invalid fill before output/report.
Type-mask0xfff->0xff negative control fails513 intended assertions in8 executed
cases; source restored byte-exact/compileall-f before all288 final positives.
Actual agent ./node_modules/.bin/tsc --noEmit passes before commit.

Prior document equals4b2a5f0 after stripping only new annotation/coverage/version.
Previous643-file immutable bundle refuses replacement without mutation and is
preserved before regeneration;641 other files identical, only backdrops.json/
manifest.json differ. Standalone/bundle CLIs repeat identically/input unchanged:
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/backdrop-refresh/. Source delivery/CI follows
within this tick. Combined exporter/spec remains started/sol: actual header/bank
selection/arena geometry/spawns/global/opcode/observed behaviour still open.
No second slice, new schedule/continuation, release or hardware claim.

Delivery: tested source8c05e471eea91226ef03730ac03e647db988b1b9 pushed main;
CI38500161764 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38500161764 . Downloaded
job115644958976 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and288 cases (252 pass/36 local-original fixtures skipped).
All288 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/backdrop-refresh/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual header/image selection/arena geometry/spawns/observed behaviour
still open.

2026-10-14: Sol tick t_mv7hfou8uatrl, one bounded M0 frame-local backdrop
placement refresh-probe slice. Clean main/fetched origin, no open PRs/issues or
in-flight work at start; direct main follows repository convention.
backdrop-dump/5 schema5 joins every stored placement record's first-word equality
probe to ALL definition lists in its own frame. Candidate definition block/slot/
header offset/hash/type/global/deleted identities retained; missing/multiple,
non-backdrop/deleted states explicit. Live backdrop candidates add conditional
32-byte record previews applying the previously proven ordered header refresh
writes to the original stored bytes. Incoming creation type never filters matches;
all unwritten bytes/coordinates retained. Global-flagged local headers remain local
probes, no application-global fallback or winning header selected. Every record
runtime_resolution=false. This supports later arena artwork/placement research,
not effective live placement/global selection/collision/spawns/behaviour.
Existing optional detached private fault reporter unchanged; malformed placement
storage exits2 before standalone/bundle output/reporting. No original content,
assets/exports/instructions/proof data or private endpoint committed/published.

Independent source traversal checks all7968 original stored records and every
local header candidate. All5090 conditional backdrop previews (69 quick/5021
ordinary) match full unmodified original helper0x40f250 returns in Unicorn2.1.4;
512 seeded conflicting header/record pairs also match exported probe previews:
5602 complete executions. Every output byte, return stack, callee-preserved
registers, header/instructions checked. Supplied stored headers/records are DATA;
no instruction/import/callback replacements and no actual loader selection,
rendering/collision/gameplay executed. Original executable SHA256 remains
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.

Eight new cases/all296 local tests pass with original/pinned KlikBack6e178b9.
Coverage: independent source spans, quick/ordinary untouched bytes, inconsistent
stored types, high header-type/fill bits, local/global flag differences, ambiguous
lists/all candidate types/no global fallback, unsigned words, aliases/gaps/reversed
pointers, absent/empty/repeated blocks, immutable standalone/bundle repeats and
late malformed refusal without output/reporting. Initial synthetic fixture lacked
final segment/block markers and expected signed deleted type; corrected before
positives (reader retains255). Placement destination-offset+1 negative control
fails both intended assertions in2 executed cases; byte-exact restoration and
compileall-f before final full296 positives. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Prior document equals43c501b after stripping only new frame probes/coverage/version.
Previous643-file immutable bundle refuses replacement without mutation and is
preserved before regeneration;641 files unchanged, only backdrops.json/manifest.json
change. Standalone/bundle CLI repeats identical/input unchanged SHA256
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/backdrop-placement-probes/. Source delivery/CI
follows within this tick. Combined exporter/spec stays started/sol: actual header/
image selection/arena geometry/spawns/global/opcode/observed behaviour remain open.
No second slice/new schedule/continuation/release or hardware claim.

Delivery: tested source8dc1c62fd98a10c9373613836f1900323277504b pushed main;
CI38501069264 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38501069264 . Downloaded
job115647888303 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and296 cases (259 pass/37 local-original fixtures skipped).
All296 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/backdrop-placement-probes/. This
delivery edit changes NOTES only; tested source unchanged. No unfinished work/
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual header/image selection/arena collision/spawns/opcode/observed
behaviour still open.

2026-10-14: Sol tick t_mv7hsghlw3g5y, one bounded M0 conditional quick-backdrop
rectangle-input slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. backdrop-dump/6 schema6
adds nullable conditional_quick_rectangle_inputs to local placement candidates:
live quick headers only, all ambiguous/local-global-flagged candidates preserved,
ordinary/deleted/non-backdrop null and missing definitions remain absent. Signed
X/Y at record2/4 survive conditional refresh; width/height at26/28 come from the
supplied header34/36. Original origin rule subtracts signed runtime words at
0x41d662/64; endpoint adds signed refreshed size. Live translation values remain
null, their state meaning/initialization unknown; explicit zero_translation_edges
are hypothetical exclusive bounds, never selected runtime/arena geometry. Zero/
negative/asymmetric values remain intact without normalization or 16-bit wrapping.
Incoming creation type never filters header candidates; globals remain unresolved.
Existing detached optional private fault reporter unchanged; malformed inputs
exit2 before either standalone/bundle output/reporting. No original content,
assets/exports/instructions/proof data or private endpoint committed/published.

Independent absolute-source traversal checks all69 original quick placement
candidates; other types null. Unmodified original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f in Unicorn2.1.4:
complete helper0x40f250, TWO SEPARATE renderer paths0x4057db..0x405804 and
0x405886..0x4058c8 execute1339 contexts/4017 paths:343 boundaries,512 seeded,
69 original candidates*7 translation pairs and one wrong unsigned expectation
(which fails). Actual origin outputs feed endpoint path unchanged. Every refreshed
byte, header, return/path stack, preserved registers and instruction span checked.
Supplied translation words/headers/records are DATA, no instructions/imports/
callbacks replaced. Intervening gates/full renderer/header selection/culling/
clipping/drawing/collision/gameplay NOT executed or claimed. Actual arena bounds,
spawns/record mutations until drawing and observed behavior remain open.

Eight new cases/all304 local tests pass with original/pinned KlikBack6e178b9.
Coverage: signed/asymmetric boundaries/negative/zero dimensions, opaque neighbors,
old record type/dimensions versus refreshed headers, all fill kinds, ambiguous
local/global flags and all other candidate types, aliases/reversed/gapped slots,
absent/empty/repeated blocks, bundle/standalone equality/immutable repeats and
late invalid header before output/reporting. Initial immutable-bundle test forgot
to update the old component manifest, caught inventory validation instead of
replacement refusal; corrected manifest hashes/version before positives.
X-offset2->3 control fails54 intended assertions (including49 boundary subtests)
in8 executed cases; source restored byte-exact and compileall-f forced before
final full304 positives. Actual agent ./node_modules/.bin/tsc --noEmit passes.

Previous document equals762faa8 after stripping only new candidate annotations/
coverage/version. Previous643-file immutable bundle refuses replacement without
mutation and is preserved before regeneration;641 unrelated files identical,
only backdrops.json/manifest.json change. Standalone/bundle CLI repeats identical,
input/executable unchanged; project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/quick-rectangle-inputs/. Source delivery/CI
follows within this tick. Combined exporter/spec stays started/sol: actual header/
image/translation selection, arenas/spawns/global/opcode/observed behavior open.
No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested sourcedb1cb033aab919fc0f5fb6f09761e804260b937a pushed main;
CI38502034928 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38502034928 . Downloaded
job115651000773 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and304 tests (266 pass/38 local-original fixtures skipped).
All304 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/quick-rectangle-inputs/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual header/image/translation selection/arena collision/spawns/
global/opcode/observed behavior still open.

2026-10-14: Sol tick t_mv7i5bhly1rkv, one bounded M0 conditional quick-backdrop
fill dispatch/call-input slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repository convention.
backdrop-dump/7 schema7 adds conditional_quick_fill_inputs to live quick placement
candidates, null for ordinary/deleted/non-backdrop; all ambiguous/local-global-
flagged candidates retained. It uses refreshed fill WORD24/image8/colors16/20.
Low nibble selects solid/mosaic/gradient; mosaic image zero falls back to solid
color16. Nonzero mosaic requires unresolved metadata; no invented0xFFFF sentinel.
Gradient high fill bit0x0100 swaps raw color arguments independently of low-byte
orientation; low flag word is fill&0xF0. Original mov/and DX then push EDX preserves
incoming high16 bits, so full flags remain unresolved rather than zero-extended.
Clipping inputs are null signed-int32 call arguments with inclusive signed-min/
32-bit-wrapping rule; no unknown live bounds calculated. All runtime_resolution/
drawing_performed false, previous artwork/records/refresh/rectangle fields unchanged.
Strict earlier artwork/bank validation unchanged (editor mosaic0 needs occupied0).
Existing detached optional private fault reporter unchanged; malformed input exits2
before standalone/bundle output/reporting. No original content/assets/instructions/
proof data/exports/private endpoint committed or published.

Independent absolute-source traversal verifies all69 original quick candidates:
24 gradient/45 mosaic, high fill bytes all0. Complete unmodified original helper
0x40f250 then fill ENTRY0x4054b0 through first CALL INPUTS execute in Unicorn2.1.4:
4411 contexts/8822 paths. Fill stops before solid4055d9/gradient4055b6/metadata405528
call instruction. Every full refreshed record/header/instruction span, saved callee
registers/entry stack/assembled arguments checked. All256 high fill bytes*six fills*
two handles=3072 contexts,343 asymmetric signed-word/int32/wrapping/clip boundaries,
512 seeded,69 originals*7 contexts,one wrong zero-extension expectation fails on
actual0xDEAD0010. No instruction/import/callback replacement. No fill import,
metadata lookup/tile loops/drawing/full renderer/caller/header selection/collision/
spawns/gameplay execution. Solid/zero fallback/high-byte swaps are synthetic
capabilities, not observed original gameplay. Original executable SHA256 remains
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f.

Eight new cases/all312 local tests pass with original/pinned KlikBack6e178b9,
compileall-f. Coverage includes independent source spans/all high fill bytes,
zero/nonzero handles, other types/missing/ambiguous/local-global definitions,
opaque neighbors, alias/reversed/gapped slots, absent/empty/repeated blocks,
strict late malformed refusal without writing/reporting, bundle/standalone/
immutable repeats. Initial original branch-count expectation was wrong (36/33);
absolute-source assertion showed24/45, corrected before final validation.
Swap-mask0x0100->0x0200 control fails258 intended assertions in8 executed cases;
source restored byte-exact/compileall-f before final312 positives. Actual agent
./node_modules/.bin/tsc --noEmit passes before commit.

Previous document equals e1e5fe6 after stripping only fill annotations/coverage/
version. Previous643-file immutable bundle refuses replacement without mutation
and is preserved before regeneration;641 files unchanged, only backdrops.json/
manifest.json change. Standalone/bundle CLI repeats identical/input/exe unchanged;
project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/quick-fill-inputs/. Source delivery/CI follows
within this tick. Combined exporter/spec remains started/sol: actual header/image/
translation/clip selection, fill imports/arenas/spawns/global/opcodes/observed behavior
remain open. No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested source78323a0f4f364c4cac915f800f987efa16f84091 pushed main;
CI38502835025 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38502835025 . Downloaded
job115653522409 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and312 tests (273 pass/39 local-original fixtures skipped).
All312 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/quick-fill-inputs/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished implementation,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual selection/fill imports/arena collision/spawns/global/opcode/
observed behavior remain open.

2026-10-14: Sol tick t_mv7ii6pr10w6ze, one bounded M0 conditional ordinary
backdrop rectangle-input slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repo convention. backdrop-dump/8
schema8 adds conditional_ordinary_rectangle_inputs to live ordinary placement
header candidates only; other types null, ambiguous/local-global-flagged matches
retained. Signed record X/Y2/4 survive refresh; original origin subtracts signed
runtime words0x41d662/64. Post-lookup endpoints add signed returned-buffer words
10/12. Live translations/returned dimensions remain null, lookup not performed.
Each local header's stored image-bank candidate adds raw/signed dimension words
and zero-translation hypothetical edges under EXPLICIT returned-words-equal-this-
stored-candidate assumption. No effective arena geometry/winner/global fallback/
metadata import result/hotspot/collision/spawn/observed behaviour claim, even with
one bank match. Stored record26/28/header34/36 never supply ordinary dimensions.
Existing artwork/refresh/quick annotations unchanged; detached optional private
fault reporter unchanged, malformed storage/metadata exits2 before writes/reporting.
No original content/assets/instructions/proof data/exports/private endpoint committed.

Independent absolute-source traversal verifies all5021 original ordinary placement
candidates, local header handles and image-bank offsets/hash/words. Unmodified
original FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f in Unicorn2.1.4:
complete refresh helper0x40f250 plus TWO SEPARATE renderer consumer spans
4057db..405804 (origin) and4058ae..4058c8 (post-metadata exclusive endpoints).
36003 contexts/108009 original path executions:343 boundary,512 seeded,all5021
originals*7 asymmetric translations and one wrong unsigned-metadata expectation
(which fails). Actual origin outputs feed the second span unchanged; supplied
buffer is DATA. Full records/headers/instruction spans/all128 stack bytes/preserved
registers/translations checked. No metadata call/import/instruction/callback
substitutions or full renderer/lookup/live selection/collision/gameplay execution.
No claim that returned metadata actually equals source bank words.

Eight new cases/all320 local tests pass with original/pinned KlikBack6e178b9,
compileall-f. Coverage includes signed/zero/negative dimensions/asymmetry, conflicting
repeated banks, local/global differences/all-type ambiguity/missing u16 slots,
opaque stored dimensions, alias/reversed/gapped slots/absent/empty/repeated blocks,
standalone/bundle repeats/previous immutable refusal, independent original spans
and late invalid refusal before outputs/reports. The repeated-bank test initially
compared cached pre-mutation bytes, corrected by parsing the final fixture before
positives. Signed metadata view <h-><H negative control fails50 intended assertions
in8 executed cases; source restored byte-exact and compileall-f before final full
320 positives. Actual agent ./node_modules/.bin/tsc --noEmit passes before commit.

Previous document equals3467705 after removing only new candidate annotation/
coverage/version. Previous643-file immutable bundle refuses replacement without
mutation and is preserved before regeneration;641 files unchanged, only
backdrops.json/manifest.json change. Standalone/bundle CLI repeats identical,
input/executable unchanged, project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/ordinary-rectangle-inputs/. Source delivery/CI
follows within this tick. Combined exporter/spec remains started/sol: actual
header/image/returned metadata/translation selection, fill imports, arenas/spawns/
global/opcode/observed behaviour still open. No second slice/new schedule/
continuation/release/hardware claim.

Delivery: tested source053bb3aaa222f0fd05ae3903d48f28c229b83cec pushed main;
CI38503743993 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38503743993 . Downloaded
job115656372828 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and320 tests (280 pass/40 local-original fixtures skipped).
All320 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/ordinary-rectangle-inputs/. This
delivery edit changes NOTES only; tested source unchanged. No unfinished work,
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual header/image/returned metadata/translation selection, arenas/
spawns/global/opcodes/observed behaviour remain open.

2026-10-14: Sol tick t_mv7iv3dg14eula, one bounded M0 conditional backdrop
image-metadata call-input slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repository convention.
backdrop-dump/9 schema9 adds conditional_image_metadata_call_inputs to live
ordinary and nonzero-image quick-mosaic placement candidates; solid/gradient/
zero-image mosaic/deleted/non-backdrop null. All local/global-flagged ambiguity
retained. Both paths push runtime context0x41d4e4, image argument and caller-stack
output pointer; live context/pointer and callee interpretation unresolved.
Quick mosaic clears EAX then loads AX: argument is zero-extended image word8.
Ordinary writes only WORD stack18 then reads DWORD18 overlapping translated
origin X at stack20. Its full rule is ((origin_x&0xFFFF)<<16)|image_word, with
origin signed record X2 minus signed runtime translation0x41d662. Live translation/
high-half/full argument null; zero_translation_argument_raw_u32 is hypothetical.
Record10 is not an input; no invented0/0xFFFF ordinary sentinel or claim that
callee uses the upper half. No actual metadata return/bank/winner/arena geometry
or behaviour inferred. Prior annotations unchanged, all runtime_resolution/
metadata_lookup_performed/drawing_performed false. Existing detached optional
private fault reporter unchanged; malformed storage exits2 before standalone/
bundle output/reporting. No original content/assets/exports/instructions/proof
data or private endpoint committed/published.

Independent absolute project traversal verifies all5021 ordinary candidates,
45 mosaic call cases and24 gradient no-call cases. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f,
Unicorn2.1.4:43485 contexts/122973 original path executions. Complete refresh
helper40f250; ordinary TWO SEPARATE spans4057db..405804 and405846..4058a9;
real origin outputs feed call assembly unchanged. Intervening culling/global
refresh gates skipped, runtime EBX1 supplied explicitly, not inferred. Quick
complete fill prologue/dispatch/assembly4054b0 stops BEFORE its first CALL.
686 signed-boundary/6144 all-high-fill-byte*fills*handles/1024 seeded contexts,
all5090 original candidates*7 asymmetric translations and one incorrect
zero-extended ordinary expectation (fails on actual0xFFF60005). Full record/
header bytes, ordinary256-byte stacks, quick saved registers/entry arguments,
call inputs/instructions checked. Original thunk414186/IAT41e5d8/ordinal109
verified from executable bytes but never called. No import/instruction/callback
substitutions, metadata lookup/full renderer/actual selection/collision/spawns/
gameplay executed or claimed.

Eight new cases/all328 local tests pass with original/pinned KlikBack6e178b9,
compileall-f. Signed/raw probes/full u16 handles/opaque neighbors/quick dispatch,
local-global ambiguity/all types/missing definitions, aliases/reversed/gapped
slots/absent/empty/repeated blocks, source spans, bundle/standalone equality/
repeats/old immutable refusal and late malformed refusal all covered.
Zero-translation argument shift16->15 control fails33 intended assertions in8
executed cases; source restored byte-exact/compileall-f before final full328
positives. Actual agent ./node_modules/.bin/tsc --noEmit passes before commit.
Previous document equalsfa77b7d after stripping only new annotations/coverage/
version. Previous643-file bundle refuses replacement without mutation and is
preserved before regeneration;641 files unchanged, only backdrops.json and
manifest.json change. Standalone/bundle CLI repeats identical/input/exe unchanged;
project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/image-metadata-call-inputs/. Source delivery/CI
follows within this tick. Combined exporter/spec stays started/sol: callee/import
results, actual selection/arena geometry/spawns/global/opcodes/observed behaviour
remain open. No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested source18d5ff2652ed392ffc076f7ae3cbcf260028a6d7 pushed main;
CI38504781947 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38504781947 . Downloaded
job115659665458 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and328 tests (287 pass/41 local-original fixtures skipped).
All328 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/image-metadata-call-inputs/. This
delivery edit changes NOTES only; tested source unchanged. No unfinished work/
continuation/new schedule/release/second slice; combined exporter/spec remains
started/sol, actual metadata callee/selection/arenas/spawns/global/opcodes/
observed behaviour remain open.

2026-10-14: Sol tick t_mv7r2uwz4gu5o, one bounded M0 type23 comparison-prefix
input slice. Clean main/fetched origin, no open PRs/issues or unfinished work at
start; direct main follows repository convention. event-dump/22 schema22 adds
comparison_prefix_storage to type23 only, both roles/frame/global scope. Original
parameter dispatch42775f/table41af64 entry23 selects4277ca: prefix at parameter4
is saved, expression evaluated, restored into BX, incremented with16-bit wrap,
carry cleared. Exported getter fields apply ONLY on normal expression return.
Conditional signed integer consumer assumes original path4284cf: caller left
versus evaluated right, prefix&7FFF selects table41b1f0 indices0..5 = equal,
not_equal, less_or_equal, less, greater_or_equal, greater. High bit purpose opaque;
unknown indices retained/null operation. Actual left/condition result remain null,
runtime_resolution=false; no assumption that every type23 opcode uses this path,
no dynamic/global/condition/string/gameplay evaluation claim. Previous expression
fields/raw words/suffixes/text lines preserved; new COMPARISON_PREFIX text line.
Existing detached optional private fault reporter unchanged; malformed supported
expressions exit2 before standalone/bundle writes or reporting. No original
assets/exports/instructions/proof data/private endpoint committed or published.

Independent source traversal/pinned-reader token walks verify all1400 original
parameters (all conditions): prefixes0:578/1:60/2:92/3:461/5:209,1378 closed integer
right expressions/22 dynamic. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
83293 complete getter/conditional numeric consumer executions. Getter covers all
65536 stored words (including unknown indices/FFFF wrap) plus1378 originals;
consumer588 signed boundary/6144 seeded/1378*7 original right expressions plus
one wrong unsigned expectation (fails). Actual original expressions execute only
for the prior proven closed integer subset;22 dynamic originals never executed.
Result/tag/BX/carry/branch/stack/preserved registers/parameter bytes and entire
mapped executable bytes checked. Original dispatch/calls/evaluator instructions
unchanged, numeric paths stop before4294a2/4294b1 condition bookkeeping. No
instructions/imports/callback substitutions or caller dispatch/live state/gameplay.
Prefix4/high bit remain synthetic capabilities, not original gameplay observations.

Eight new cases/all336 local tests pass with original/pinned KlikBack6e178b9,
compileall-f; actual agent ./node_modules/.bin/tsc --noEmit passes (locked dev
compiler restored via npm ci --include=dev --ignore-scripts; no agent code/lockfile
change). Coverage includes all65536 prefixes, wrap/unknown masks, both roles/all
parameter types/scopes, dynamic/empty/fault shapes, source reconstruction/readable
annotations, immutable bundle repeats and late malformed refusal before reporting.
Initial bundle test used wrong manifest field path instead of file; corrected.
Initial full run caught13 old schema21 assertions; updated expected version22
without changing those test contracts. Mask7FFF->FFFF control fails two intended
assertions in8 executed cases; source restored byte-exact/compileall-f before
final full336 positives. Previous JSON/text equal3836d27 after removing only new
annotations/coverage/version. Previous643-file bundle refuses replacement without
mutation and is preserved before regeneration;640 files identical, only
 events.json/events.txt/manifest.json change. All JSON/text/bundle CLI repeats
identical; original project/executable unchanged, project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/comparison-prefixes/. Source delivery/CI follows
within this tick. Combined exporter/spec remains started/sol: actual opcode/
condition/global semantics, placement selection/arenas/spawns/observed behaviour
remain open. No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested source3b7aed9d24f826c7b3fb46ab80e055ec7d781aca pushed main;
CI38525648698 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38525648698 . Downloaded
job115725237880 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and336 tests (294 pass/42 local-original fixtures skipped).
All336 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/comparison-prefixes/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice; combined exporter/spec remains started/sol:
actual opcode/condition/global semantics, arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7rskov6dkuy, one bounded M0 immediate scalar
parameter-getter input slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repository convention.
event-dump/23 schema23 adds scalar_getter_storage for exact WORD types
3/4/5/10/12/14/15/17/26/32/34 and DWORD types2/24/29, both roles/frame/global.
Original generic dispatch42775f/table41af64 selects42779d (WORD MOVZX) or4277a5
(DWORD MOV). At payload0, stored raw unsigned bits and all opaque suffix bytes
are retained. Conditional EAX transport zero-extends WORD or preserves DWORD;
BX0/carry clear, incoming DX preserved rather than a new expression value tag.
Caller units/signedness/flags/sentinels/opcode/global meanings stay unknown,
runtime_resolution=false. Prior type26 action frame-target annotation unchanged;
prior pinned-reader type15 expression token view coexists but does NOT prove this
generic getter evaluates it (actual getter transports its prefix WORD). No original
type15 or other unobserved supported types promoted to gameplay observations.
Existing private optional detached fault reporter unchanged; truncated supported
scalars exit2 before JSON/text/bundle output or reporting. No original assets/
exports/executable instructions/proof data/private endpoint committed or published.

Independent absolute project traversal verifies all793 originals: types2:7,
10:197,14:16,17:246,26:2,29:307,32:18. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f in Unicorn2.1.4:
75420 complete dispatcher/getter executions. All65536 WORD values through shared
handler;336 exact-type bit boundaries/three incoming DX patterns;7168 seeded cases;
all793 original parameter spans*three incoming DX values;one wrong sign-extension
expectation (fails on actual EAX0000FFFF). EAX/full EBX/EDX/carry/ECX/callee-preserved
registers, entire128-byte stack/input bytes/mapped executable checked. No
instruction/import/callback substitutions or live caller/event/gameplay execution.
Initial private source walker used wrong reader attribute/raw block identifier and
row header extent; corrected to ident4/header14 against independent raw spans
before final proof. Full original/source counts agree with the exporter.

Eight new cases cover every WORD value for every exact supported type, DWORD
bit boundaries/suffixes, other types/both roles/type15 dual view/type26 coexistence,
strict truncated shapes, all scopes/readable text/raw reconstruction, standalone/
bundle byte equality/repeats/immutable refusal and late bad scalar refusal before
writing/reporting. Initial test used wrong frame-target field name; corrected.
Two old tests intentionally updated for newly supported scalar validation: audio
non-audio type5 fixture now supplies its required WORD; truncated condition type26
now refuses just as actions do, while valid conditions retain no frame-target
annotation. Schema expectations updated22->23 without other contract changes.
WORD EAX bit15-toggle control fails two intended assertions in two executed cases;
source restored byte-exact/compileall-f before final positives. Local final test/
TypeScript checks and delivery evidence follow below within this tick.
Evidence: agent state data/furries/scalar-getters/. Combined exporter/spec stays
started/sol: actual opcode/caller/global/placement selection/arenas/spawns/observed
behaviour still open. No second slice/new schedule/continuation/release/hardware claim.

Final local validation: compileall-f and all344 tests pass with original/pinned
KlikBack6e178b9 enabled after negative-control restoration. Actual agent
./node_modules/.bin/tsc --noEmit passes. Previous JSON/text equals ec34199 after
stripping only scalar annotation/coverage/version; all old fields and text lines
preserved. Previous643-file bundle refuses replacement without mutation and
is preserved before regeneration;640 files identical, only events.json/
events.txt/manifest.json change. Standalone JSON/text/bundle CLI repeats identical,
input/executable unchanged. Project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Tested source delivery and exact-head CI verification follow within this tick.

Delivery: tested source4c17fa19051de6ea3008b009e3844a7d5b41fa5d pushed main;
CI38527462996 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38527462996 . Downloaded
job115731096381 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and344 tests (301 pass/43 local-original fixtures skipped).
All344 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/scalar-getters/. This delivery edit
changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice; combined exporter/spec stays started/sol:
actual opcode/caller/global semantics, arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7sibf38fv5k, one bounded M0 parameter-address
getter input slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/24 schema24
adds address_getter_storage for exact generic getter table entries: header-address
types6/7/8/9/11/13/18/19/20/21/25/27/28/30/31/33/35/36/37/38/39 select427784;
type40 selects427791 and returns payload address+4. Dispatcher42775f/table41af64
returns BX0/carry clear, preserves incoming DX; no numeric/string tag invented.
Relative offsets0/4 are conditional on reaching that dispatch, never runtime
addresses derived from source offsets. Stored byte count is not a runtime memory
bound. Payload not dereferenced, caller interpretation unknown/runtime_resolution
false; audio/position/group views retained separately. State-dependent type1 and
helper-calling type16 excluded; no extrapolated table beyond0..40, text/NUL/encoding/
caller/event/global/condition/gameplay semantics. No new payload minimum invented;
previous audio/position/etc. strict checks remain. Existing detached optional
private fault reporter unchanged; malformed storage exits2 before JSON/text/bundle
writing or reporting. No original content/assets/exports/instructions/proof data/
private endpoint committed/published.

Independent absolute source traversal verifies all2502 original parameter headers/
spans: types6:870/7:21/9:1150/13:122/18:110/19:29/38:41/39:159. Type40 and other
absent supported types remain synthetic capabilities. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
20421 complete original dispatcher/getter executions. Exact0..40 table entries,
1584 boundary/address/payload/DX cases,66 final-page/wrapped-address cases,11264
seeded cases,all2502 originals*3 incoming DX values,one wrong header->payload
expectation (fails). Type40 wrapsFFFFFFFC+4 to unmapped zero without dereference.
EAX/full EBX/EDX/ECX/preserved registers/carry/128-byte stack/parameter bytes/entire
mapped executable verified; no instruction/import/callback substitutions or
caller/event/gameplay execution. Private proof reads original bytes only.

Eight new cases cover exact types/full unknown-u16 exclusion, header versus payload
address, empty/arbitrary/non-NUL storage, both roles/scopes, retained audio/position/
group fields/raw reconstruction, source spans/counts, text/bundle equality/repeats/
immutable refusal and late broken header refusal before writes/reporting. Initial
original test omitted its expected-count constant; added independently traversed
counts before final positives. Old schema23 expectations updated24 without other
contract changes. Header offset0->2 negative control fails two intended assertions
in two executed cases; source restored byte-exact and compileall-f forced. All352
local tests pass with original/pinned KlikBack6e178b9 enabled; compileall-f and
actual agent ./node_modules/.bin/tsc --noEmit pass before commit.

Previous JSON/text equals21896fa after stripping only address annotations/coverage/
version; old fields/text lines unchanged. Previous643-file bundle refuses replacement
without mutation and is preserved before regeneration;640 files identical, only
 events.json/events.txt/manifest.json change. Standalone JSON/text/bundle CLI repeats
identical,input/executable unchanged, project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/address-getters/. Tested source delivery and
exact-head CI verification follow within this tick. Combined exporter/spec remains
started/sol: actual opcode/caller/global semantics, placement selection/arenas/spawns/
observed behaviour still open. No second slice/new schedule/continuation/release/
hardware claim.

Delivery: tested source3d84e54dd2fac9563d26d3992a2fcc3df77f9834 pushed main;
CI38529631423 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38529631423 . Downloaded
job115738123815 log verifies actual source/pinned-reader checkout outputs,
Python3.10, compileall and352 tests (308 pass/44 local-original fixtures skipped).
All352 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/address-getters/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice; combined exporter/spec remains started/sol:
actual opcode/caller/global semantics, arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7t8246awarw, one bounded M0 type22 expression
parameter-getter slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/25 schema25
adds expression_getter_storage to exact type22 only, both roles/frame/global.
Original generic dispatch42775f/table41af64 selects4277c1, calls42a417 wrapper,
starts tokens at parameter6/payload2, skips stored prefix. On normal evaluation
return EAX/DX are evaluator result/tag, BX0/carry clear. Closed integer probes
transport prior proven raw32 results/DX0; CPU faults have no invented normal
return, unsupported dynamic/string/shape forms have no inferred numeric result.
General normal-return contract explicitly conditional; runtime_resolution=false,
caller meanings unknown. Type15 scalar/type23 comparison/other reader token views
unchanged. Existing detached optional private reporter unchanged; malformed
expressions exit2 before standalone/bundle output/reporting. No original assets/
exports/executable instructions/proof data/private endpoint committed/published.

Independent absolute source walk verifies all2461 original type22 spans:2172
actions/289 conditions, all prefix0;2112 closed integer literals/349 dynamics.
Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
72821 complete original dispatcher/exact getter/wrapper/evaluator executions,
72817 normal returns/four divide errors. All65536 prefix words,27 literal/DX
boundaries,405 arithmetic pairs,four focused recursive cases,512 seeded recursive
streams,2112 original parameter byte spans*three incoming DX patterns and one
incorrect prefix-transport expectation (fails). EAX/DX/BX/carry/128-byte return
stack/preserved regs/parameter bytes/entire mapped executable checked; faults stop
before recovery. No instruction/import/callback substitutions,dynamic/string/
caller/event/gameplay execution. Initial private proof selected similar427788
code; exact table audit corrected handler to4277c1 before final execution.
Unicorn retains pending exception state after stopped divide errors: reusing that
CPU gave vector8 on the next fault; fresh CPU after each fault gives correct
vector0 without any runtime instruction changes. Preserve this isolation rule.

Eight new cases cover signed/raw returns,ignored prefixes/opaque suffixes,
compound/recursive/wrapped/zero-divisor inputs,CPU faults versus normal returns,
dynamic/string/empty refusal,exact type22/both roles/scopes,retained prior views,
source-byte counts/reconstruction,text/bundle equality/repeats/immutability and
late invalid refusal before writes/reporting. First full run caught missing
original expected-count constants; inserted independent source-walk counts.
Schema24 expectations updated25 with other old contracts intact. EAX bit0-toggle
control fails two intended assertions in two executed cases; source restored
byte-exact and compileall-f forced before final all360 local positives with
original/pinned KlikBack6e178b9 enabled. Actual agent ./node_modules/.bin/tsc
--noEmit passes before commit. No agent code/lockfile change.

Previous JSON/text equalsf9e6717 after stripping only new annotation/coverage/
version; all old fields/text lines preserved. Previous643-file immutable bundle
refuses replacement without mutation and is preserved before regeneration;640
files unchanged,only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats byte-identical,input/executable unchanged. Project
SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence: agent state data/furries/expression-getters/. Tested source delivery
and exact-head CI verification follow within this tick. Combined exporter/spec
remains started/sol: actual opcode/caller/global/placement selection/arenas/spawns/
observed behaviour still open. No second slice,new schedule,continuation,release
or hardware claim.

Delivery: tested sourcee543a998bc75460ed961efff4ccd6b187076505c pushed main;
CI38531928279 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38531928279 . Downloaded
job115745587085 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and360 tests (315 pass/45 local-original fixtures skipped).
All360 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/expression-getters/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice; combined exporter/spec stays started/sol:
actual opcode/caller/global semantics,arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7txs9acwzfp, one bounded M0 type16 packed position
parameter-getter slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/26 schema26
adds position_getter_storage to exact type16 only, both roles/frame/global.
Original dispatch42775f/table41af64 selects4277ac: payload address+4/BX0 calls
position helper42a2a6, packs returned X into EAX high16/Y low16, clears BX/carry.
Helper success/failure carry is discarded, not a new getter success indicator;
failure coordinate values remain unknown. Conditional absolute branch uses stored
reference sign bit, returns packed raw X/Y/DX0. Nonnegative refs need live object
state/no inferred result; prior reference candidates/sentinels remain unchanged.
Caller meanings unknown/runtime_resolution=false; no actual arena/spawn/global/
opcode/event/gameplay resolution. Existing optional detached private fault reporter
unchanged; existing strict malformed position refusal precedes all output/reporting.
No original assets/exports/executable instructions/proof data/endpoint published.

Independent absolute raw-program walk verifies three original action parameters:
references4023/402B/402A, flags8, stored X/Y0, selector words17DA/0866/0810. All
three remain live-state unresolved. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
34755 complete original dispatcher/getter/helper/cached-selection executions:
33578 absolute (all32768 sign-bit references included),662 synthetic Cartesian,
515 failed cached selections. Signed axis/flag boundaries/512 seeded origins,
three original words under explicitly changed synthetic reference/selector
contexts plus wrong axis-order rejection. Helper carry1/0 observed before packing;
all getter normal returns BX0/carry0. EAX/DX where supported,preserved registers/
return stack/parameter bytes/full image checked,only supplied cache pointers/helper
one-byte cache flag allowed in relative contexts. Initial oracle wrongly assumed
X low/Y high; actual execution disproved it and the independent expectation was
corrected before final proof. No instruction/import/callback substitutions or
original selection/caller/event/gameplay execution. Original live state unknown.

Eight new tests cover all65536 reference words,signed/raw axis boundaries,
helper flag-discard contract,unknown failure/live-state values,exact type16/both
roles/scopes,retained position/raw views,strict full extent,original source spans,
readable annotations,standalone/bundle equality/repeats/immutable refusal and late
short-position refusal before any write/report. Old schema25 expectations updated
26 without other contract changes. First full run: all368 local tests pass with
original/pinned KlikBack6e178b9 enabled; compileall-f and actual agent
./node_modules/.bin/tsc --noEmit pass. Source restoration/negative control/bundle
compatibility and delivery evidence follow below within this tick.
Evidence: agent state data/furries/position-getters/. Combined exporter/spec
remains started/sol: actual opcode/caller/global/placement selection/arenas/spawns/
observed behaviour still open. No second slice/new schedule/continuation/release/
hardware claim.

Final local validation: reversed X/Y packed-word control fails two intended
assertions in two executed cases; restored source byte-exact/compileall-f before
final all368 positives with original/pinned reader enabled. Saved source/test/docs/
roadmap hashes unchanged after restoration. Previous JSON/text equals f02cde5
when stripping only position_getter_storage/coverage/version and POSITION_GETTER
lines; all prior fields/text lines preserved. Previous643-file immutable bundle
refuses replacement without mutation and is preserved before regeneration;640
files identical, only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats byte-identical, original project/executable unchanged.
Project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Actual agent tsc gate passed; no agent source/lockfile changed. Tested source
commit/push and exact-head CI verification follow within this tick.

Delivery: tested sourcec75c7e7314cbc86c1db0884f589ffc14f98eb091 pushed main;
CI38534277466 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38534277466 . Downloaded
job115753257497 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and368 tests (322 pass/46 local-original fixtures skipped).
All368 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/position-getters/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice; combined exporter/spec remains started/sol:
actual opcode/caller/global semantics,selection/arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7uni35e37bf, one bounded M0 type1 conditional
object parameter-getter slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repository convention. event-dump/27
schema27 adds object_getter_storage to exact type1, both roles/frame/global.
Original dispatch42775f/table41af64 selects42776a, tests byte41c866. Zero gate
returns HEADER address/BX0/carry0/DX preserved without payload dereference.
Nonzero gate calls426bcd, reads selection WORD at parameter4/payload0, copies
helper ESI into EAX on either normal return branch. Helper carry1 -> BX0/carry0;
helper carry0 -> helper BX retained/carry1. Active DX/helper effects/pointer
validity depend on live state. Existing editor ref at payload2 remains separate;
no gate/branch/actual pointer/global/opcode/caller mapping inferred. resolved_eax
null/runtime_resolution false. Strict type1 six-byte minimum and optional private
detached fault reporter unchanged; malformed storage exits2 before output/report.
No original assets/exports/executable bytes/proof scripts/private endpoint committed.

Independent absolute source-program walk verifies all974 original type1 parameters:
690 condition/284 action,760 frame/214 global; first and second WORD differ in all,
all first WORDs nonnegative. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
73563 complete original dispatcher/getter/helper/cached-selection executions:
66510 inactive(all65536 first WORDs),3526 cached success,3527 cached failure.
All255 nonzero gate values with positive/negative selectors,512 seeded payload/
flag/counter contexts,974 byte-exact original parameters under three explicitly
supplied synthetic contexts and wrong failure-carry rejection. No original live
selection/event/caller/gameplay execution, instruction/import/callback substitutions.
Full return stack/input/image/cache/record bytes and preserved regs checked;
actual helper flags/counter wrapping included. Initial oracle put record inside
cache snapshot; separated the supplied regions before final proof. Active FFFF
special-selector probe changes EDI to426bdd, fails generic preservation expectation;
diagnostic saved, excluded from successful cached-selection proof. No special
context/semantics or original selection claim inferred from it.

Eight new tests cover all65536 first WORDs, distinct editor ref,conditional gate/
helper carry branches,unknown pointer validity,exact type1/both roles/scopes,
opaque tail/raw reconstruction,existing candidates,strict short input,original
source words/counts,text/bundle agreement/repeats/immutability and late malformed
refusal before output/reporting. First full run all376 local tests pass with
original/pinned reader enabled. WORD0->WORD2 negative control fails three intended
assertions in three executed cases; restored byte-exact and compileall-f forced.
Final original-enabled suite/actual agent tsc and compatibility evidence below.
Evidence: agent state data/furries/object-getters/. Combined exporter/spec remains
started/sol: live global/opcode/caller/selection/arenas/spawns/observed behaviour
open. No second slice/new schedule/continuation/release/hardware claim.

Final local validation: all376 tests pass with original/pinned KlikBack6e178b9
fixtures enabled after byte-exact negative-control restoration; compileall-f and
actual agent ./node_modules/.bin/tsc --noEmit pass before commit. Previous JSON/
text equals58deed7 after removing only object_getter_storage/new coverage/version
and OBJECT_GETTER lines; every prior field/text line remains. Old643-file immutable
bundle refuses replacement without mutation, preserved before regeneration;640
files byte-identical, only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats byte-identical; original project/executable unchanged.
Project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/test/docs/roadmap hashes and private runtime/compatibility/negative/
test/typecheck evidence in data/furries/object-getters/. No agent source/lockfile
change. Tested source delivery and exact-head CI verification follow within this
same tick; exporter/spec remains started/sol. No second slice/new schedule/
continuation/release/hardware claim.

Delivery: tested sourcef9325ab8254a09435ac97824004f4c0568da5e13 pushed main;
CI38536688949 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38536688949 . Downloaded
job115761170416 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and376 tests (329 pass/47 local-original fixtures skipped).
All376 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in agent state data/furries/object-getters/. This delivery edit
changes NOTES only; tested source unchanged. No unfinished work/continuation/new
schedule/release/second slice; combined exporter/spec remains started/sol:
actual caller/opcode/global/selection/arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7vd79kgwlpr, one bounded M0 type42 fixed-value
parameter-getter slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/28 schema28
adds fixed_value_getter_storage to exact type42, both roles/frame/global. Original
dispatch42775f/table41af64 entry42 ->4277d9 loads DWORD at parameter4/payload0,
WORD at parameter12/payload8, increments BX16 without masking, clears carry and
preserves incoming DX. Middle four bytes/suffix retained; no expression evaluation,
comparison alias, signedness/units/player/global/opcode/caller meanings inferred.
Type42 is absent from this original game: capability only, runtime_resolution=false.
Strict ten-byte payload minimum fails before output/reporting; existing optional
private detached fault reporter unchanged. No original assets/executable/proof
scripts/private endpoint committed or published.

Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f, Unicorn2.1.4:
66897 complete dispatcher/getter executions: all65536 control WORDs,336 Cartesian
DWORD/control/DX/carry boundaries,1024 seeded middle/suffix/input contexts and one
wrong-mask expectation rejected. Full EAX/EBX/EDX/carry/preserved-register/input/
128-byte return-stack/whole mapped PE checks; no instruction/import/callback
substitutions or caller/event/gameplay execution. Independent absolute source
traversal checks8160 parameters and confirms zero type42 instances.

Eight new tests cover wrap/high bit/opaque spans,exact type/both roles/scopes,
lossless reconstruction,text/bundle equality/repeats/immutability,all short extents,
late invalid refusal before writes/reporting and original absence. All384 local
tests pass with original/pinned KlikBack6e178b9 enabled. WORD-offset8->6 control
fails two intended assertions in two executed cases; source restored byte-exact,
compileall-f forced, final all384 positives pass. Actual agent
./node_modules/.bin/tsc --noEmit passes; no agent source/lockfile changed.

Evidence: agent state data/furries/fixed-value-getters/. Compatibility and delivery
verification follow within this tick. Combined exporter/spec remains started/sol:
actual caller/opcode/global/selection semantics,arenas/spawns/observed behaviour
still open. No second slice/new schedule/continuation/release/hardware claim.

Compatibility: previous JSON/text equals8ff1bce after stripping only the new
coverage/version (no original type42 annotations exist). All prior fields and
text lines preserved;640 of643 bundle files identical,only events.json/events.txt/
manifest.json change. Old immutable bundle refused replacement without mutation,
preserved before regeneration. Standalone JSON/text/bundle CLI repeats identical;
input/executable unchanged,project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/test/docs/roadmap hashes match final restored/tested files.

Delivery: tested source53070c95559b4f089b67aa5b061b661c2e7b4e3c pushed main;
CI38538911812 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38538911812 . Downloaded
job115768544593 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and384 tests (336 pass/48 local-original fixtures skipped).
All384 passed locally with the original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in data/furries/fixed-value-getters/. This delivery edit changes
NOTES only; tested source unchanged. No unfinished work/continuation/new schedule/
release/second slice/hardware claim. Combined exporter/spec stays started/sol:
actual caller/opcode/global/selection semantics,arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7vq3mritw0l, one bounded M0 type45 expression
parameter-getter slice. Clean main/fetched origin,no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/29 schema29
adds exact type45_getter_storage,both roles/scopes. Original dispatch42775f/table
41af64 entry45 ->427788 calls full wrapper42a417/evaluator42a42e starting at
parameter6/payload2,ignoring prefix. Normal return EAX/DX=evaluator result/tag,
BX0/carry0. Exact lone03FF string returns unknown parameter address+10/DX1 with
bounded literal bytes; no resolved pointer/encoding/filesystem/caller meaning.
Closed proven integers return EAX/DX0,CPU faults no normal return,recovery unknown.
Compound/recursive/dynamic strings/empty shapes unresolved. All seven originals
(five action/two condition,frame-local) independently verified from source bytes;
all general/live semantics remain false. Type22/23/scalar views unchanged,
adjacent46 unannotated. Existing strict expression validation/private detached
unexpected-fault reporter unchanged; invalid storage exits2 before writes/report.
No original assets/executable/proof scripts/private endpoint committed/published.

Unmodified executable SHA256f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f,
Unicorn2.1.4:66548 full dispatcher/getter/wrapper/evaluator executions,66112 string/
434 integer/two divide faults. All65536 prefixes,42 string/27 integer boundaries,
405 independent numeric pairs,four recursive integer probes,512 seeded byte
strings,seven original byte-exact parameters under three incoming DX contexts,
wrong parameter+6 pointer rejected. Full mapped PE/input/128-byte return stack/
preserved registers and output pointer/bytes/tag/BX/carry checked. Fault recovery
unexecuted,fresh CPU after faults,no instruction/import/callback substitutions or
live dynamic/compound-string/caller/event/gameplay execution. Large-string test
initially exceeded synthetic record WORD extent; kept large decoder/reconstruction
proof separate from valid record-sized integration before positive verification.

Evidence: agent state data/furries/type45-getters/. Final suite/negative-control/
compatibility/typecheck/delivery evidence follows within this tick. Combined
exporter/spec stays started/sol:actual opcode/caller/global/selection/arena/spawn/
observed behaviour open. No second slice/new schedule/continuation/release/
hardware claim.

Final local validation: all393 tests pass with original/pinned KlikBack6e178b9
enabled after pointer-offset+1 control fails two intended assertions in two
executed cases. Source restored byte-exact/compileall-f forced before final
positives. Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent source/
lockfile changed. Prior JSON/text equals61d9fc6 after removing only new type45
annotations/coverage/version and TYPE45_GETTER lines; every earlier field/line
preserved. Old643-file immutable bundle refused replacement without mutation,
preserved before regeneration;640 files identical,only events.json/events.txt/
manifest.json change. Standalone JSON/text/bundle CLI repeats byte-identical;
original project/executable unchanged. Project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/test/docs/roadmap hashes and runtime/negative/compatibility/test/
typecheck evidence in data/furries/type45-getters/. Tested source push/exact-head
CI verification follow within this tick; exporter/spec remains started/sol.
No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested sourcedf37e10b08af17633d24d8712c6b226536439135 pushed main;
CI38540034751 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38540034751 . Downloaded
job115772226538 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and393 tests (344 pass/49 local-original fixtures skipped).
All393 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in data/furries/type45-getters/. This delivery edit changes NOTES
only; tested source unchanged. No unfinished work/continuation/new schedule/release/
second slice/hardware claim. Combined exporter/spec stays started/sol:actual caller/
opcode/global/selection semantics,arenas/spawns/observed behaviour remain open.


2026-10-14: Sol tick t_mv7w2xebk3f5c, one bounded M0 remaining header-address
getter slice. Clean main/fetched origin, no open PRs/issues or unfinished work at
start; direct main follows repository convention. event-dump/30 schema30 extends
existing address_getter_storage to exact types41/43/44/47/48/49. Original generic
dispatch42775f/table41af64 through entry49 independently selects427784 for all
six: unchanged parameter HEADER EAX, BX0/carry0, incoming DX preserved. Adjacent
46 is a different expression-wrapper entry, remains excluded. Payload not read;
no object/value/string/player/global/identifier/encoding/caller interpretation
inferred. Existing coverage/fields/layout validation/private detached optional
fault reporting preserved, runtime_resolution false. Late malformed type48 exits2
before JSON/text/bundle writes/report. No original assets/executable/proof scripts/
private endpoint committed or published. Combined exporter/spec stays started/sol.

Independent absolute program walk traverses all8160 source parameters:20 type48
instances,6 conditions/14 actions,2 frames/18 globals; other five added types absent.
All are12-byte parameters with four raw payload WORDs:1009/2040/2002/2031/2032/2042
followed by three zero WORDs, counts1/3/3/5/5/3 respectively. Initial fixture
expectation overgeneralised the first instance's role/scope/words; independent
complete traversal corrected it before final tests/proof. Storage equality is
not identifier resolution or a scalar return. Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f,Unicorn2.1.4:
3601 complete dispatcher/getter executions,432 Cartesian boundaries,36 minimal
headers at mapped-region/high-address edges with unmapped bytes after them,3072
seeded cases,60 byte-exact original runs and wrong payload-pointer rejection.
Every run checks reads only parameter type/table entry/return address,full mapped
PE/input/128-byte return stack/EAX/EBX/EDX/ECX/preserved regs/carry. No instruction/
import/callback substitutions or caller/event/gameplay/live selection execution.

All397 local tests pass with original/pinned KlikBack6e178b9 enabled after a
type48 header-offset0->4 negative control fails two intended assertions in two
executed cases. Source restored byte-exact and compileall-f forced before final
positives. Four new cases cover minimal/opaque payloads,both roles/scopes/text,
late malformed refusal before output/report and independent original storage;
existing exact-type/full-range/reconstruction/bundle tests updated for the new
family. Actual agent ./node_modules/.bin/tsc --noEmit passed before commit; no
agent source/lockfile changed. Previous JSON/text equals62603f0 after stripping
only newly supported types' address annotations and version; all prior fields/
coverage/text retained. Old643-file immutable bundle refused replacement without
mutation,preserved before regeneration;640 files identical,only events.json/
events.txt/manifest.json change. Standalone JSON/text/bundle CLI repeats identical;
original project/executable unchanged. Project SHA256 remains
98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.

Evidence/source/docs/test/roadmap hashes in agent state
data/furries/late-address-getters/. Tested source push and exact-head CI
verification follow within this tick. Exporter/spec remains started/sol:actual
caller/opcode/global/selection/placement/arena/spawn/observed behaviour open.
No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested sourceb7483000756d2d8d2c425d05c26702d667952102 pushed main;
CI38541392112 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38541392112 . Downloaded
job115776746035 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and397 tests (347 pass/50 local-original fixtures skipped).
All397 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in data/furries/late-address-getters/. This delivery edit changes
NOTES only; tested source unchanged. No unfinished work/continuation/new schedule/
release/second slice/hardware claim. Combined exporter/spec stays started/sol:
actual caller/opcode/global/selection/placement/arenas/spawns/observed behaviour open.

2026-10-14: Sol tick t_mv7wsolsmw92f, one bounded M0 type46 expression
parameter-getter capability slice. Clean main/fetched origin, no open PRs/issues
or unfinished work at start; direct main follows repository convention.
event-dump/31 schema31 adds exact type46 expression_storage/type46_getter_storage
for both roles/scopes. Original dispatcher42775f/table41af64 entry46 ->427788
calls full wrapper42a417/evaluator42a42e at parameter6/payload2, ignores prefix;
normal EAX/DX=evaluator result/tag, BX0/carry0. Exact lone03FF string returns
unknown parameter address+10/DX1 with bounded bytes, no encoding/caller meaning.
Closed proven integers return EAX/DX0; CPU faults have no normal return/recovery
unknown. Dynamic/compound/recursive strings unresolved, general/live semantics
false. Type22/23/45 and every earlier annotation remain unchanged. Independent
absolute source traversal verifies all8160 parameters and zero type46 instances:
capability only, no newly decoded original gameplay. Late malformed type46 now
fails2 before JSON/text/bundle writes/report; optional private detached unexpected
fault reporter unchanged. No assets/executable/proof scripts/private endpoint
committed or published.

Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f,Unicorn2.1.4:
66527 complete dispatcher/getter/wrapper/evaluator runs (66091 string,434 integer,
two CPU faults). All65536 prefixes,42 byte-string boundaries,27 integer/tag
boundaries,405 independently calculated arithmetic pairs,four recursive integer
cases,512 seeded strings,one wrong pointer rejected. Full mapped PE/input/128-byte
return stack/preserved regs/EAX/pointer bytes/DX/BX/carry checked. Fresh CPU after
faults; no recovery/instruction/import/callback substitutions or live dynamic/
caller/event/gameplay execution. Unused copied type45 original-shape branch was
removed from private proof before rerunning; type46 absence checked directly.

Nine new tests cover prefix/raw bytes/string pointer/integer/fault contracts,
exact types/both roles/scopes/dynamic candidates/reconstruction/text/bundle
repeats/immutability/strict late refusal and independent original absence.
All406 local tests pass with original/pinned KlikBack6e178b9 enabled. Type46
pointer-offset+1 control fails one intended assertion in three executed cases;
source restored byte-exact/compileall-f forced before final positives. Initial
full suite had three stale schema/version expectations, corrected before final
all406 positives. Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent
source/lockfile changed.

Evidence: agent state data/furries/type46-getters/. Compatibility and delivery
verification follow within this tick. Combined exporter/spec remains started/sol:
actual caller/opcode/global/selection/placement/arena/spawn/observed behaviour
open. No second slice/new schedule/continuation/release/hardware claim.

Compatibility: prior JSON equals796ae57 after stripping only new type46 coverage/
version (original has no type46 annotations); readable text unchanged except
version. All prior fields/lines retained. Old643-file immutable bundle refused
replacement without mutation, preserved before regeneration;640 files identical,
only events.json/events.txt/manifest.json change. Standalone JSON/text/bundle
CLI repeats byte-identical; original project/executable unchanged. Project SHA256
remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/docs/test/roadmap hashes match final restored/tested files. Tested
source push/exact-head CI verification follow within this tick; exporter/spec
stays started/sol. No second slice/new schedule/continuation/release/hardware claim.

Delivery: tested sourceeccee99355234186ec465a13fac15b9d73c958fe pushed main;
CI38543743168 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38543743168 . Downloaded
job115784571158 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and406 tests (355 pass/51 local-original fixtures skipped).
All406 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision. Evidence/CI
snapshots/job log in data/furries/type46-getters/. This delivery edit changes NOTES
only; tested source unchanged. No unfinished work/continuation/new schedule/release/
second slice/hardware claim. Combined exporter/spec stays started/sol:actual caller/
opcode/global/selection/placement/arenas/spawns/observed behaviour remain open.

2026-10-14: Sol tick t_mv825nanoqht5, one bounded M0 random expression input
slice. Clean main/fetched origin, no open PRs/issues or unfinished work at start;
direct main follows repository convention. event-dump/32 schema32 adds exact
four-byte01FF random_inputs. Original dispatcher42a474/table41b2b8 entry1 ->
42882a evaluates from token+4 via42a424, passes low EAX WORD to421991;16-bit
state at41c8ce updates (state*7AB7+1)&FFFF, result=(updated*bound_u16)>>16,
zero-extended EAX/DX0. Bound0 still changes state. Conditional adjacent integer
literal+FEFF/FDFF stop retains raw/signed32 and low16 input/token IDs; wrapper
restores argument start and outer dispatcher leaves stop unconsumed. Dynamic,
compound, recursive/string/missing argument shapes unresolved. No live state,
seeding/call order/containing expression/opcode/event/gameplay result inferred;
runtime_resolution false and prior closed-integer evaluator still refuses random.

Independent absolute source traversal checks all8160 parameters:39 exact random
occurrences,all actions (30 frame/9 global),all adjacent literal+FEFF:12(30),
300(1),400(1),900(2),5(1),3(1),4(2),2(1). Unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f in Unicorn2.1.4
executes132019 complete dispatcher/evaluator/helper paths:all65536 states,
all65536 bounds,200 signed/high-word/state/stop boundaries,512 seeded contexts,
234 byte-exact original runs and one rejected wrong32-bit-bound expectation.
EAX/tag/cursor/state mutation/preserved regs/input/128-byte return stack/full
mapped PE except expected state WORD checked. No instruction/import/callback
substitutions or actual game initialisation/containing-expression execution.

Seven new tests cover exact code/extent,low-word boundaries/both stops,unsupported
shapes,both roles/scopes/all expression types,text/reconstruction,immutable bundle
repeats,late invalid refusal before output/reporting and independent original
storage. All413 local tests pass with original/pinned KlikBack6e178b9 enabled;
bound maskFFFF->7FFF control fails nine intended assertions in two executed
cases,source restored byte-exact/compileall-f forced before final positives.
Initial neighbour-token test supplied a too-short object-expression fixture;
corrected to its existing required header extent before all413 positives.
Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent source/lockfile changed.

Prior JSON fields and readable text equal877522d after stripping only random
annotations/coverage/version. Every previous view retained. Old643-file immutable
bundle refused replacement without mutation,preserved before regeneration;640
files identical,only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats byte-identical,input/executable unchanged. Project
SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Late bad random extent now exits2 before JSON/text/bundle writes/report; existing
optional detached private fault reporter unchanged. No original assets/executable/
proof scripts/private endpoint committed or published. Evidence and saved restored
source/docs/test/roadmap hashes in agent state data/furries/expression-random/.
Tested source push/exact-head CI verification follow within this tick.
Exporter/spec stays started/sol:caller/opcode/global/selection/placement/arena/
spawn/observed behaviour remain open. No second slice/new schedule/continuation/
release/hardware claim.

Delivery: tested sourcedb9ab6d85183ebb7cfb30d31f084e44f1eedd596 pushed main;
CI38561717736 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38561717736 . Downloaded
job115844156245 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and413 tests (361 pass/52 local-original fixtures skipped).
All413 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the CI-tested revision/commit tree.
Evidence/CI snapshots/job log in data/furries/expression-random/. This delivery
edit changes NOTES only; tested source unchanged. No unfinished work/continuation/
new schedule/release/second slice/hardware claim. Combined exporter/spec stays
started/sol:live state/caller/opcode/global/selection/placement/arenas/spawns/
observed behaviour remain open.

2026-10-14: Sol tick t_mv82vci2qvtz7, one bounded M0 indexed runtime
value-table expression input slice. Clean main/fetched origin, no open PRs/issues
or unfinished work at start; direct main follows repository convention.
event-dump/33 schema33 adds exact four-byte02FF value_table_inputs. Original
system dispatcher42a474/table41b2b8 entry2 ->42876c evaluates argument through
full42a424/42a42e, decrements AX/masks0xF, reads DWORD at41d282+index*4, sets DX0.
Conditional adjacent literal+FEFF/FDFF retains raw/signed32,low16,index/byte offset
and unconsumed-stop cursor. Zero selects15,1 selects0,17 aliases1; no clamp.
Live table contents/initialisation/ownership/global names/caller meanings remain
unknown/runtime_resolution false; existing whole-expression constant evaluator
still refuses this dynamic token. Unsupported/string/compound/recursive arguments
remain explicit. Earlier token/getter/raw fields/text and coverage preserved.
Existing strict validation/private optional detached unexpected-fault reporter
unchanged; non-four-byte02FF now exits2 before JSON/text/bundle writes/reporting.
No original assets/executable/proof scripts/private endpoint committed/published.

Independent absolute source traversal checks all8160 parameters and45 original
tokens:43 actions/two conditions,41 frame/four global; all literal+FEFF.
Arguments/counts1(4),2(6),3(4),4(4),5(4),6(4),7(7),9(6),10(6). Eight new tests
cover slot aliases/signed/high-word boundaries,both stops,exact extent/neighbours,
unsupported forms,both roles/scopes/all expression types,text/reconstruction,
immutable bundle repeats,late malformed refusal before writes/report and direct
original source agreement. All421 local tests pass with original/pinned reader
6e178b9 enabled after slot-decrement omission control fails89 intended assertions
in8 executed cases; source restored byte-exact/compileall-f forced. An old random
neighbour fixture used an oversized02FF; adjusted to its now-supported exact
four-byte shape. First full run overlapped the negative-control mutation and is
not accepted as evidence; final full positives ran after restoration separately.
Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent source/lockfile changed.

Evidence in agent state data/furries/expression-value-table/. Final executable
proof/compatibility/source push/exact-head CI verification follow within this
tick. Combined exporter/spec remains started/sol:live state/caller/opcode/global/
selection/placement/arenas/spawns/observed behaviour open. No second slice/new
schedule/continuation/release/hardware claim.

Runtime proof: unmodified FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f in Unicorn2.1.4
executes66619 complete dispatcher/handler/argument/enclosing evaluator paths:
all65536 argument words,300 boundaries,512 seeded argument/table contexts,270
byte-exact original runs under three synthetic tables,wrong zero-slot rejected.
Every execution checks selected DWORD read address/extent,unchanged table/full
mapped PE,input/128-byte return stack,EAX/EDX/EBX/ECX/cursor/ESP/preserved ESI/EBP.
The first extended-register proof used an incorrect EBX high-word expectation;
corrected separately for dispatcher/evaluator, diagnostic retained before the
final complete positive run. No instruction/import/callback substitutions or
actual table initialisation/live contents/containing expressions/gameplay.

Compatibility: previous JSON/text equals24d1c38 after stripping only new token
annotations/coverage/version; all prior fields/lines retained. Old643-file
immutable bundle refused replacement without mutation,preserved before
regeneration;640 files identical,only events.json/events.txt/manifest.json change.
Standalone JSON/text/bundle CLI repeats byte-identical,input/executable unchanged.
Project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/test/docs/roadmap hashes match final restored/tested files. Tested
source push and exact-head CI verification follow within this tick; no second
slice/new schedule/continuation/release/hardware claim.

Delivery: tested sourcebf95eb813a68b89498aa041150809114859976f7 pushed main;
CI38564219502 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38564219502 . Downloaded
job115852680982 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and421 tests (368 pass/53 local-original fixtures skipped).
All421 passed locally with original enabled after negative-control restoration.
Saved source/docs/test/roadmap hashes match the tested commit tree. Evidence/CI
snapshots/job log in data/furries/expression-value-table/. This delivery update
changes NOTES only; tested source unchanged. No unfinished work/continuation/new
schedule/release/second slice/hardware claim. Combined exporter/spec stays
started/sol:live state/caller/opcode/global/selection/placement/arenas/spawns/
observed behaviour remain open.


2026-10-14: Sol tick t_mv83l2visnkl2, one bounded M0 closed integer
value-table argument input slice. Clean main/fetched origin, no open PRs/issues
or unfinished work at start; direct main follows repository convention.
event-dump/34 schema34 extends value_table_inputs only beyond the existing
adjacent-literal view: closed numeric arithmetic/prefix/recursive arguments
bounded by a stored top-level FEFF/FDFF stop. Existing proven integer evaluator
supplies conditional signed/raw32 value, low16 input, slot/byte offset and token
IDs; CPU divide faults have no slot/value/normal-return cursor. Unsupported,
dynamic/string/incomplete argument shapes remain unresolved, including a dynamic
tail after apparent faulting arithmetic. Opaque suffix never supplies the stop.
Actual live table/containing expression/caller/gameplay remain unresolved, general
expression_evaluation/runtime_resolution false. Original45 table references are
still adjacent literals: capability expansion, no newly decoded original gameplay.

Unmodified original dispatcher42a474/handler42876c/wrapper42a424/evaluator42a42e
restores the argument-start cursor then advances ONLY the first token's length.
New conditional views retain after_first_argument_token and payload offset:
compound 1+16 returns at plus; leading minus/recursive token advances4 bytes.
This is not the enclosing expression's result or full parse cursor. Legacy
literal+stop annotations are byte-for-byte unchanged. Strict input checks and
optional detached private unexpected-fault reporting preserved; malformed late
integer extent refuses JSON/text/bundle writes/reporting. No assets/executable/
proof scripts/private endpoint committed or published.

Independent Unicorn2.1.4 runs5949 complete original instruction paths against
FF2xmas.exe SHA256 f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
1487 arithmetic/wrapping/prefix/recursive/nested/priority/association cases,
both recursive/top-level stops,512 seeded pairs, both dispatcher and argument
evaluator. All2974 exported views match independently calculated expected
values/slots/cursors or fault-only shapes. Eight IDIV CPU faults occur before
any table read; fresh CPU per run, no normal return/recovery claimed. Normal
runs check EAX/lowDX/EDI/ESP/EBX/ECX/preserved ESI/EBP/128-byte return stack;
all runs check unchanged full PE/table/input. Wrong full-argument-cursor
expectation rejected against actual returned EDI. Unsupported tokens deliberately
stored after the top-level stop are never executed. No instruction/import/
callback substitutions, original live-table/containing-expression/gameplay run.

Seven new cases cover arithmetic/boundaries/recursive/prefix/cursor/fault/unknown
shapes, exact legacy preservation, both roles/scopes/all expression types/text,
lossless program reconstruction/bundle repeats and late malformed refusal.
Previous unsupported-shape fixtures now exclude the newly proven arithmetic
and recursive forms. All428 local tests pass with original/pinned KlikBack
6e178b9 enabled; closed-argument decrement omission control fails22 intended
assertions in seven executed cases. Source restored byte-exact and compileall-f
forced before final full suite; no concurrent source mutation during positives.
Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent source/lockfile change.

Prior original JSON/text equals8b174ab after stripping only new coverage/version:
all old token/getter/raw fields and readable lines retained. Old643-file immutable
bundle refused replacement without mutation, preserved before regeneration;
640 files identical, only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats byte-identical, project/executable unchanged.
Project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence/restored source/test/docs/roadmap hashes in agent state
 data/furries/value-table-arguments/. Tested push/exact-head CI verification
follow within this tick. Exporter/spec stays started/sol:live state/caller/opcode/
global/selection/placement/arenas/spawns/observed behaviour remain open.
No second slice/new schedule/continuation/release/hardware claim.


Delivery: tested source2c01ae81585c6b6ce2300e2f083590c5c52c5e56 pushed main;
CI38566675627 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38566675627 . Downloaded
job115861003975 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and428 tests (375 pass/53 local-original fixtures skipped).
All428 passed locally with original enabled after negative-control restoration.
Saved source/test/docs/roadmap hashes match the CI-tested commit tree. Evidence/CI
snapshots/job log in data/furries/value-table-arguments/. This delivery edit
changes NOTES only; tested source unchanged. No unfinished work/continuation/new
schedule/release/second slice/hardware claim. Combined exporter/spec stays
started/sol:live state/caller/opcode/global/selection/placement/arenas/spawns/
observed behaviour remain open.

2026-10-14: Sol tick t_mv84atb5uc2e1, one bounded M0 closed integer random
argument input slice. Clean main/fetched origin, no open PRs/issues or unfinished
work at start; direct main follows repository convention. event-dump/35 schema35
extends random_inputs only beyond the preserved adjacent-literal view: closed
numeric arithmetic/prefix/recursive arguments bounded by stored top-level FEFF/
FDFF. Existing proven integer evaluation supplies conditional signed/raw32 value,
low16 RNG bound and token IDs. CPU IDIV faults have no bound/value/normal cursor;
unsupported/dynamic/string/incomplete arguments remain unresolved, including a
dynamic tail after apparent faulting arithmetic. Opaque suffix cannot supply a
stop. Existing whole-expression evaluation still refuses random; actual state,
seeding/call order/caller/containing expression/gameplay remain unknown and
runtime_resolution/general expression_evaluation false.

Unmodified dispatcher42a474/handler42882a/wrapper42a424/evaluator42a42e restores
argument-start EDI then advances only its FIRST token's extent. New normal views
retain after_first_argument_token/payload offset, not the full argument cursor.
Helper421991 transports low16 EAX, updates state16 at41c8ce and scales as before;
computed bound0 still advances state. Existing literal views and earlier table/
getter/raw/token fields remain unchanged. Strict malformed-token validation and
optional detached private unexpected-fault reporter preserved; late malformed
integer extent exits2 before JSON/text/bundle writes/reporting. No assets,
executable, proof scripts or private endpoint committed/published.

Independent Unicorn2.1.4 proof executes5949 complete unmodified original
instruction paths against FF2xmas.exe SHA256
f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f:
1487 arithmetic/wrapping/priority/association/prefix/recursive/nested cases,
both top-level/recursive stops and512 seeded arithmetic pairs. All2974 exported
views match independent values/bounds/cursors or fault shapes. Eight IDIV faults
occur before RNG state mutation; fresh CPU per run, no recovery claimed. Normal
EAX/DX/EDI/ESP/EBX/ECX/preserved ESI/EBP/128-byte stack and all-run full PE/input
checks pass, with only the expected state WORD written. Wrong full-argument
cursor rejected. No instruction/import/callback substitutions or actual live
RNG state/containing-expression/gameplay execution. First emulator run copied
the value-table handler's EBX high-word expectation; corrected to the actual
random path's zero EBX using original instructions, diagnostic retained before
final complete proof. Initial parser test used absent build/klikback/src;
rerun with the actual pinned external reader path succeeds.

Seven new cases cover low-word/wrapping boundaries, recursion/prefix/cursor,
fault/unsupported shapes, exact legacy preservation, both roles/scopes/all
expression types, text/lossless reconstruction/bundle repeats and late refusal.
Existing unsupported random fixtures now exclude newly proven closed forms.
All435 local tests passed with original/pinned KlikBack6e178b9 enabled before
negative control. Closed bound FFFF->7FFF control fails nine intended assertions
in seven executed cases; source restored byte-exact/compileall-f forced before
final positives. Actual agent ./node_modules/.bin/tsc --noEmit passes; no agent
source/lockfile changed. Final full positives/compatibility/push/exact-head CI
verification follow within this tick. Evidence in agent state
 data/furries/random-arguments/. Exporter/spec remains started/sol:live state,
caller/opcode/global/selection/placement/arenas/spawns/observed behaviour open.
No second slice/new schedule/continuation/release/hardware claim.

Final validation: all435 local tests pass with original enabled after source
restoration; duplicate assertion-key cleanup then passes all seven affected
cases and forced compileall. Prior original JSON/text equals20f22d3 after
stripping only new coverage/version; all39 original random references remain
literal-only, so this is capability expansion. Old643-file immutable bundle
refused replacement without mutation,preserved before regeneration;640 files
identical, only events.json/events.txt/manifest.json change. Standalone JSON/
text/bundle CLI repeats byte-identical,input/executable unchanged. Project SHA256
remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Saved source/test/docs/roadmap hashes match final tested files. Tested push and
exact-head CI verification follow within this tick; no second slice/new schedule/
continuation/release/hardware claim.

Delivery: tested source3cc186f681ab2069bd60c42f9d90ff87aace0ba8 pushed main;
CI38569034813 completed/success on that exact revision:
https://github.com/jarvis-jhk/funny-furries/actions/runs/38569034813 . Downloaded
job115869049965 log verifies actual source/pinned-reader checkout outputs,
Python3.10,compileall and435 tests (382 pass/53 local-original fixtures skipped).
All435 passed locally with original enabled after negative-control restoration;
all seven affected cases also passed after duplicate assertion-key cleanup.
Saved source/test/docs/roadmap hashes match the tested commit tree. Evidence/CI
snapshots/job log in data/furries/random-arguments/. This delivery edit changes
NOTES only; tested source unchanged. No unfinished work/continuation/new schedule/
release/second slice/hardware claim. Combined exporter/spec stays started/sol:
live state/caller/opcode/global/selection/placement/arenas/spawns/observed
behaviour remain open.

2026-10-14: Sol tick t_mv84notqw2ptj, one bounded M0 conditional runtime
value-table write action slice. Clean main/fetched origin, no open PRs/issues or
unfinished work at start; direct main follows repository convention.
event-dump/36 schema36 adds value_table_action_inputs for exact system type-1
ACTION opcodes3=set,4=subtract,5=add. Original signed dispatch426542/table41b27c
selects42871e/428738/42872b; the subtract/add order is independently proven,
not borrowed from a newer SDK. Full helper428745 evaluates index then operand
through42a417/42a42e, preserving record EDI and advancing by first parameter
length. Slot=(low16 index-1)&F; same DWORD table41d282 as02FF reads. Operand
transport is full32bits, updates wrap. Exactly two validated type22 parameters
supply conditional closed-integer inputs; other layouts/dynamic/string/stop-tail
forms unresolved. Ordered index/operand CPU faults precede table writes; unknown
index never certifies an operand fault. Set exports a conditional stored DWORD;
add/sub retain unknown previous value and no final DWORD. Actual event execution,
row/disabled flags/live table/ownership/names/gameplay remain unresolved,
runtime_resolution/general opcode/expression semantics false.

Independent absolute source walk checks all9306 records and62 original actions:
54 set(42 frame/12 global),four frame subtract,four frame add. All indices are
literal;45 operands literal,17 frame set operands dynamic. Unmodified original
FF2xmas.exe SHA256 f16de343e48ad50cdf9b36118a790ece6980c24539dbcaf11ce5ce8eb7e0210f
runs197946 complete Unicorn2.1.4 action-dispatch/handler/helper/evaluator paths:
all65536 index words for each operation,675 boundaries,512 seeded contexts,six
recursive/wrapping cases,135 byte-exact original closed-action runs under three
synthetic tables,nine CPU faults and an actual rejected wrong-opcode-order probe.
All690 synthetic exported views match independent values/slots/faults. Exact
selected table reads/writes,full mapped PE except expected DWORD,input,normal
EDI/ESP/EAX/lowDX/EBX/ECX/preserved ESI/EBP/128-byte caller stack checked.
No instruction/import/callback substitutions or dynamic original/live gameplay
execution. First oracle reused a CPU after IDIV; the next fault did not raise.
Fresh CPU for each fault and after it fixes the proof setup; initial diagnostic
retained before the final complete successful run.

Seven new tests cover exact opcode/type/role/layout,slot aliases/signed/high-word
bounds/full-DWORD operands,variable lengths/prefix/suffix/recursive wrapping,
ordered faults/dynamic refusal,frame/global text/raw reconstruction,immutable
bundle repeats,late actual malformed-expression refusal before output/reporting
and independent original storage. Initial synthetic project replacement omitted
container-length/address updates; replaced with complete valid containers, and
late-refusal tests now assert the intended literal-extent error. Thirteen old
suite assertions only needed schema/version35->36 updates. All442 local tests
pass with original/pinned KlikBack6e178b9 enabled after negative-control restore;
subtract/add swap causes183 intended failures in seven executed cases. Source
restored byte-exact/compileall-f forced before full final positives. Actual
agent ./node_modules/.bin/tsc --noEmit passes; no agent source/lockfile changed.

Prior original JSON/text equals e2919ca after stripping only new record views/
coverage/version; all earlier annotations/raw fields/lines retained. Old643-file
immutable bundle refused replacement without mutation,preserved before rebuild;
640 files identical,only events.json/events.txt/manifest.json change. Standalone
JSON/text/bundle CLI repeats identical,input/project/executable unchanged.
Project SHA256 remains98c6d714104bbf9334fcf1aa4b14ab6b25f771fdf25cbe96a48e8291e991f7c0.
Evidence/restored source/test/docs/roadmap hashes in agent state
 data/furries/value-table-actions/. Tested push/exact-head CI verification follow
within this tick. Exporter/spec remains started/sol:live table/caller/other opcodes/
global/selection/placement/arenas/spawns/observed behaviour open. No second slice/
new schedule/continuation/release/hardware claim.
