"""Release allowlist checks; no local content or private endpoints may leak."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in root.rglob('*'):
    if not path.is_file():
        continue
    assert path.suffix.lower() not in {'.cca', '.gam', '.cox', '.gox', '.wav', '.mid'}, path
    assert path.name not in {'arena.ff', 'import.json', 'selected.json'}, path
    raw = path.read_bytes()
    for forbidden in (b'/report/' + b'usr', b'dm:+' + b'49'):
        assert forbidden not in raw, (path, forbidden)
print('Package audit passed:', root)
