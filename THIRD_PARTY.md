# Licensing and dependencies

Funny Furries engine, exporter, launcher and packaging code: copyright 2026
Funny Furries contributors, GPL-3.0-or-later. See COPYING. Original game content
is not covered by this licence and is never distributed by this project.

The first-start importer uses KlikBack by Justaddwater (GPL-3.0-or-later),
pinned to commit 6e178b9470206f71871417dec852fbfa24cd01b9:
https://github.com/just-addwater/KlikBack . Its complete source and licence
are included in the release's source archive. No changes are made to it.

The launcher bundles CPython (PSF licence), Tcl/Tk (Tcl/Tk licence), OpenSSL
(Apache-2.0) and PyInstaller's bootloader (GPL with its distribution exception).
Runtime notices are in the launcher `_internal` directory and `licenses/`.

The native game links SDL2, SDL2_image and SDL2_mixer (zlib licence), and their
image/audio dependencies. Linux packages use Ubuntu 22.04 runtime packages;
Windows packages use MSYS2 UCRT64 packages. Package versions, copyright/licence
notices and corresponding-source download locations are included under
`licenses/`. System graphics, audio drivers and the C library remain the host's.

The corresponding Funny Furries and KlikBack source is supplied separately as
`funny-furries-source.tar.gz` beside every binary release. Packaging scripts and
pinned dependency locations are included. No original game assets, recordings,
executables, levels or decompiled projects are in any release archive.
