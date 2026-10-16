# Funny Furries

An SDL2 reimplementation of Funny Furries 2 Xmas (Bastiaan de Jong, 1999).
The test release plays all ten of the original's arenas with **up to four players**
(controllers and two keyboard layouts), free for all or 2 vs 2, on one screen or
**online** through [Warpzone](https://github.com/jarvis-jhk/warpzone) rooms (with
relay fallback) and ranked queues, with rollback netcode, on Linux, Windows and
Steam Deck. In the start menu X/punch picks the arena.

**Mods** add arenas, weapons, rules, skins and sounds — plain text and pictures,
no code, so a modded online match stays in sync. Get them in the Warpzone
launcher's Mods tab (a room shares its host's mods with everyone who joins) or
try a folder with `--mod`. Examples: [`mods/`](mods) (a snowball arsenal, a
night arena, low gravity); how to make your own: [MODDING.md](docs/MODDING.md).

Download a test version from [Releases](https://github.com/jarvis-jhk/funny-furries/releases).
Extract the package and start `Play-Funny-Furries.exe` on Windows or `play.sh`
on Linux/Deck. Choose **your own** full-version `funnyfurries.zip` or
`FF2xmas.cca` at first start. No Python or developer tools are needed.
Original graphics, sound, levels and game files are never included or uploaded.

On Deck, import in Desktop Mode, run `install.sh`, then add the installed
Funny Furries entry to Steam as a non-Steam game. No sudo required.
See [installation, controls and known limits](docs/RELEASE.md).

Pad controls: stick/D-pad move, A jump, X punch, B/right trigger weapon,
Y/left trigger jetpack, Start play/pause. First pad is blue, second red.
This is an early preview; timings and collision details are approximate.
Physical Deck/two-pad feedback is welcome.

For engine builds and reference comparisons see [PLAYING.md](docs/PLAYING.md).
The local-only research exporter is documented in [PROJECT-BUNDLE.md](docs/PROJECT-BUNDLE.md).
Engine/tool code is GPL-3.0-or-later; original game content remains its author's.
See COPYING and THIRD_PARTY.md.
