#!/usr/bin/env python3
"""Pack each mod directory into the archive Warpzone serves: the mod's files at the
archive root (Warpzone unpacks it to .../files/), byte-identical on every run."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pack(mod: Path, out: Path) -> Path:
    manifest = json.loads((mod / 'warpzone-mod.json').read_text())
    archive = out / f"{manifest['name']}-{manifest['version']}.zip"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(p for p in mod.rglob('*') if p.is_file() and p.name != 'warpzone-mod.json'):
            info = zipfile.ZipInfo(path.relative_to(mod).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes())
    return archive


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'build' / 'mods'
    for mod in sorted(p for p in HERE.iterdir() if (p / 'warpzone-mod.json').is_file()):
        print(pack(mod, out))


if __name__ == '__main__':
    main()
