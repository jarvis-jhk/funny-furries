# Funny Furries 0.8.0 — music and Jan's 0.7.0 play-test

This preview plays all ten of the original's arenas with two to four players on
controllers or the two keyboard layouts, free for all or 2 vs 2, on one screen or
online. Movement, weapons and devices are based on the original, with approximate
timing and collision details. It is not the complete original game. Automatic
updates are not included yet.

New in 0.8.0 (Jan's play-test of 0.7.0, checked against the original's event rows):
the original's music, title song in the menus and game song in a match, played by a
small built-in synthesizer (M switches it off and on); the first start shows a
progress window while it imports your copy, instead of seeming not to start; fire
from the flamethrower passes through walls; the jetpack puffs smoke while it fires;
explosions throw harder, a furry falling onto a bomb is thrown up instead of only
slowed; health, fuel and weapons are only picked up when they change something, as
in the original; the pause text sits in the middle of the screen. The first start
after the update imports your copy once more by itself.

New in 0.7.0 (fixes from Jan's play-test of 0.6.0, checked against the original's
event rows): bubbles from underwater fans look and move like the original's (a
small ring every 12-23 ticks, slow rise up the whole column, pushed by draughts,
gone at the surface); moving platforms start the way the original's markers say
and turn around when they run into each other; steps up to eight pixels are walked
up without jumping (the top corners of level 3); a furry can land and stand on
the other's head; the ice gun and rocket launcher push the shooter back (mods:
`recoil`); rockets no longer fly down through one-way tops; bouncing bombs rest
on their bottom edge instead of sinking into the scoreboard; the jetpack shows on
the furry's back while there is fuel. The first start after the update imports
your copy once more by itself.

New in 0.6.0 (fixes from Jan's play-test of 0.5.0): the original's other nine
arenas (X/punch in the start menu, `--level N`); weapons appear in the hand only
while firing and the punch plays the original's punching fist; jump, landing,
spring, splash, jetpack, hit, wall-hit and pickup sounds; the ice gun no longer
hits its shooter when fired to the left; up at the water's surface jumps out (the
right ice ledge of level 1 can be reached from the water); fans under water blow
bubbles; floor springs no longer fire when walked over; the sky is open above the
top edge; bombs stay until set off, and bouncing bombs bounce lower and lower and
then explode; the pause text is centred; a start with an unchanged copy no longer
redoes the import. The first start after the update imports your copy once more
by itself.

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

## Online play

Online play goes through Warpzone, the shared online service of these games:
rooms with a short code, a relay when two home routers cannot reach each other
directly, and ranked matches. Everyone needs this same version and the same
original copy imported. The first time you play online the game asks for a
name (3 to 16 letters, digits, `_` or `-`); it is shared with every Warpzone
game on this computer.

In the player menu, the players at one computer first join with A as usual
(one to three of them), then:

- **Host:** press H (or Back on a controller). The screen shows a six-letter
  room code such as `K7QM3X`; it is already copied to the clipboard. Send it to
  the others. Y/jetpack or Tab switches free for all / 2 vs 2; Start or Enter
  begins once everyone is in.
- **Join:** press J, type or paste (Ctrl+V) the code and press Enter. On the
  Deck, Steam+X opens the on-screen keyboard.
- **Ranked:** press R (or RB on a controller), pick 1 vs 1, free for all (four
  players) or 2 vs 2 and press Enter/A. One player per device. The match starts
  as soon as the matchmaker has found everyone; first to three round wins.
  Every game reports the result and the final game state; the server rates the
  match when they agree.

The Warpzone launcher and website can also start the game straight into a room
(`--warpzone-join`, `--warpzone-host`).

The lobby and the top right of the screen show each player's round trip and
whether the connection is direct or relayed. Escape/Back leaves. The game
predicts the other players and corrects itself when their real input arrives
(rollback), so short network hiccups do not stop play. "WAITING FOR NETWORK"
means nothing arrived for a while.

Without a connection to the Warpzone server, H and J fall back to the game's
own join codes (such as `8KQ2-M4XP-9ZTRA`, or the host's address on the same
home network), which work through most home routers but have no relay.

## Mods

Mods add arenas, weapons, rules, skins and sounds. They are plain pictures and
text, never code. In the Warpzone launcher, the Mods tab of Funny Furries
installs them; the game loads the active set at every start and the menu lists
it. X / punch in the player menu switches between the original arena and mod
arenas. Hosting a Warpzone room shares your mods and arena: everyone who joins
downloads exactly that set first. Every mod version on Warpzone is checked by a
moderator before anyone else can download it.

Without Warpzone, start the game with `--mod FOLDER` (several times for several
mods). The three example mods are attached to this release as ZIP files; unpack
one and pass its folder. Making mods: [MODDING.md](MODDING.md).

## Play and report problems

The game opens in the player menu. Each player presses A (or their keyboard jump
key) to join and B to leave; Y switches free for all / 2 vs 2; Start or Enter
begins. Pads take seats in connection order: BLUE, RED, GREEN, YELLOW. In
2 vs 2 blue+green play red+yellow. Stick/D-pad moves, A jumps, X punches,
B or right trigger fires, Y or left trigger uses the jetpack. Start pauses,
Back/Escape returns to the menu. Keyboard BLUE: arrows, Ctrl punch, Shift
weapon, slash jetpack. RED: F/H move, T jump, Z punch, A weapon, Q jetpack.
P pauses; R restarts. Holding jump repeats on landing.

Complete a match, let the next round start, then unplug/replace one controller.
Compare jumps, stopping, springs, platforms, swimming and weapons with the
original. Send the action/location/player and a description of the mismatch.
Physical two-to-four-pad play, Steam Input mappings and Deck sound/fullscreen remain
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
6. Tag only that tested source (`v0.8.0` for the music release), push the tag,
   and upload the already checked binary/source archives, the example mod ZIPs
   (`mods/pack.py`) and SHA256SUMS as a GitHub prerelease. Confirm the release is published and
   every uploaded asset downloads with the expected hash. Record remaining human
   checks in NOTES, mark `furries-test-release` done, send Jan the release URL.
