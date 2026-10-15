# funny-furries
Funny Furries 2 Xmas: JARVIS's own SDL2 reimplementation of the 1999 Click &amp; Create brawler (Bastiaan de Jong), up to 4 controllers on one screen, Linux/Windows/Deck, later rollback online

Export all supported local research data with one command:

```
python3 tools/export_project.py orig/game.cca --klikback-src /path/to/KlikBack/src
```

The [combined research bundle](docs/PROJECT-BUNDLE.md) contains lossless event
structure, object artwork metadata, PNG/WAV/MIDI files and raw placement data.
See the [local project index](docs/EXPORTER.md) for reader requirements.
A native SDL2 development prototype now plays an asset-free 1v1 practice arena.
See [building and controls](docs/PLAYING.md). Original game data and generated
exports are never bundled in this repository.
