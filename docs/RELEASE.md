# Funny Furries 0.1.0 — two-player test release

This preview plays arena 1 with two controllers or one keyboard. Movement,
weapons and devices are based on the original, with approximate timing and
collision details. It is not the complete original game. Four players, other
arenas, online play and automatic updates are not included yet.

## Windows

Extract `funny-furries-windows-x86_64.zip` fully into a folder. Double-click
`Play-Funny-Furries.exe`. No Python, compiler or SDL installation is needed.
Keep the `_internal` folder and all DLLs beside the launcher.

## Linux and Steam Deck

Extract `funny-furries-linux-deck-x86_64.tar.gz`. Run `play.sh` in its folder.
On Deck, use Desktop Mode for the first import; the file chooser uses the
trackpad/touchscreen. Run `install.sh` to install into your user account and
create an application-menu entry plus a desktop shortcut. No sudo is needed.
You can then add Funny Furries to Steam as a non-Steam game and use Game Mode.
The installed entry starts fullscreen. A desktop terminal can run `./play.sh`
or `./play.sh --fullscreen`. Linux x86_64 with glibc 2.35+ is required; the same
build targets SteamOS 3. No physical Deck certification is claimed yet.

## Your own game copy

At first start select your own full-version `funnyfurries.zip` or `FF2xmas.cca`.
You may also select `FF2xmas.exe` if its CCA file is in the same folder. The
import takes several seconds and then starts the game. The demo is unsupported.
Original art, sound and arena data are read locally from your copy; they are
not included in these downloads, uploaded or modified. No game-data download
is performed. Your original game does not need to run under Wine/Proton.

Subsequent starts reuse the checked local import. Windows stores it in
`%LOCALAPPDATA%/funny-furries`; Linux/Deck uses
`$XDG_DATA_HOME/funny-furries` or `~/.local/share/funny-furries`. To change the
source, start the launcher with `--reimport`. If local files are damaged, the
picker opens again. `--practice` opens our asset-free practice arena.

## Play and report problems

Two pads: stick/D-pad moves, A jumps, X punches, B or right trigger fires,
Y or left trigger uses the jetpack. Start closes help or pauses. First pad
controls BLUE, second RED. Keyboard BLUE: arrows, Ctrl punch, Shift weapon,
slash jetpack. RED: F/H move, T jump, Z punch, A weapon, Q jetpack.
P pauses; R restarts; Escape exits. Holding jump repeats on landing.

Complete a match, let the next round start, then unplug/replace one controller.
Compare jumps, stopping, springs, platforms, swimming and weapons with the
original. Send the action/location/player and a description of the mismatch.
Physical two-pad play, Steam Input mappings and Deck sound/fullscreen remain
open checks for this test release. Automated virtual-pad matches are verified.

Unexpected launcher/import/game faults send only the app version, OS class
and fixed category to the public ntfy topic. No usernames, paths, logs or
original content are sent. The relay opens a deduplicated GitHub issue and
notifies this project's maintenance queue. Delivery is best-effort and never
blocks play or exit. Set `FF_NO_REPORT=1` to opt out. Ordinary missing or
unsupported game copies are not reported.

## Maintainer publication gate

1. Start from a clean main, read CLAUDE/NOTES and run relevant importer/launcher
   tests with the pinned reader and a locally owned protected original.
2. Type-check the agent with its real local TypeScript binary before code
   commits. Commit/push tested work on main. No original files or private
   endpoints may be tracked or shipped.
3. Dispatch `Release packages` on the exact intended main revision. It builds
   Linux/Deck on Ubuntu 22.04 and Windows natively on UCRT64, at most two
   compiler jobs, freezes the importer/GUI/Python, bundles runtime libraries,
   runs native tests and exercises the packaged launcher/renderer with synthetic
   assets on both OSes. No release is published by the build workflow.
4. Require both jobs plus ordinary exporter/native CI to pass. Download logs
   and verify actual `git rev-parse HEAD` output, test and packaged-smoke output.
   Download the exact artifacts. Locally run the Linux frozen launcher with the
   real protected full ZIP, then run imported renderer/game-loop smoke and
   repeat launch. Check the GUI picker under a display. Inspect all archives
   for original content and private markers; check licences/source/SHA256SUMS.
5. Keep the live ntfy → issue → maintenance-queue relay running, with the private
   queue URL only in its local config. No new scheduler job is needed. A controlled
   anonymous transport probe must be received, deduplicated and cleaned up.
6. Tag only that tested source (`v0.1.0` for the first release), push the tag,
   and upload the already checked binary/source archives and SHA256SUMS as a GitHub prerelease. Confirm the release is published and
   every uploaded asset downloads with the expected hash. Record remaining human
   checks in NOTES, mark `furries-test-release` done, send Jan the release URL.
