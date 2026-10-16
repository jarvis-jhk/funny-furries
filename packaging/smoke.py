"""Exercise the actual frozen launcher and isolated native package, without original data."""
import os
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path('tests').resolve()))
from test_arena_import import fixture
from tools import import_arena, launcher

package = Path('build/package/funny-furries').resolve()
binary = package / ('Play-Funny-Furries.exe' if os.name == 'nt' else 'Play-Funny-Furries')
env = dict(os.environ, FF_NO_REPORT='1', SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
# No development DLL directory can hide a missing packaged dependency.
if os.name == 'nt':
    env['PATH'] = os.path.join(os.environ['SystemRoot'], 'System32') + ';' + os.environ['SystemRoot']
with tempfile.TemporaryDirectory(prefix='furries package ü ') as directory:
    home = Path(directory)
    fixture(home / 'bundle', wind=True)
    target = home / 'arena-v7-synthetic'
    import_arena.import_arena(home / 'bundle', target, 0)
    launcher.save_selection(home, target)
    screenshot = home / 'frame.bmp'
    args = [str(binary), '--home', str(home), '--smoke', '1500', '--screenshot', str(screenshot)]
    a = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
    assert screenshot.is_file() and screenshot.read_bytes().startswith(b'BM'), (a.returncode, a.stdout, a.stderr)
    frame = hashlib.sha256(screenshot.read_bytes()).hexdigest()
    screenshot.unlink()
    b = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
    assert a.returncode == b.returncode == 0, (a.returncode, a.stdout, a.stderr, b.returncode, b.stderr)
    assert screenshot.is_file() and hashlib.sha256(screenshot.read_bytes()).hexdigest() == frame, 'Repeated renderer output differs'
    assert a.stdout == b.stdout and '1500' in a.stdout, (a.stdout, b.stdout)
    four = subprocess.run([str(binary), '--home', str(home), '--smoke', '1500', '--players', '4', '--teams',
                           '--screenshot', str(screenshot)], env=env, capture_output=True, text=True, timeout=30)
    assert four.returncode == 0 and '1500' in four.stdout, (four.returncode, four.stdout, four.stderr)
    lobby = subprocess.run([str(binary), '--home', str(home), '--smoke', '60', '--lobby'], env=env,
                           capture_output=True, text=True, timeout=30)
    assert lobby.returncode == 0, (lobby.returncode, lobby.stderr)
    practice = subprocess.run([str(binary), '--practice', '--smoke', '1000'], env=env,
                              capture_output=True, text=True, timeout=30)
    assert practice.returncode == 0, practice.stderr
    print('Frozen launcher, synthetic PNG/WAV import, isolated native runtime, Unicode user path and repeat match passed.')
    print(a.stdout, practice.stdout)
