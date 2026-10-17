#!/usr/bin/env python3
"""First-start import and desktop launcher. Only the user's machine sees game data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import struct
import sys
import tempfile
import threading
import zipfile
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import export_project, import_arena, project_index

VERSION = '0.8.0'
TOPIC = 'https://ntfy.sh/funny-furries-faults-a93c6b4e12d8'
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
PACKAGE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else ROOT
MAX_INPUT = 32 * 1024 * 1024
# The Warpzone launcher sets this to the copy it found on the machine (descriptor [[data]] id ff2xmas).
WARPZONE_DATA = 'WARPZONE_DATA_FF2XMAS'
KEPT = 'original-FF2xmas.cca'


def data_home():
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    return base / 'funny-furries'


def source_bytes(path):
    path = Path(path)
    if path.is_dir():
        candidates = [p for p in path.iterdir() if p.name.lower() == 'ff2xmas.cca']
        if len(candidates) != 1:
            raise project_index.InputError('Choose the folder containing FF2xmas.cca, or the original ZIP.')
        path = candidates[0]
    elif path.suffix.lower() == '.exe':
        return source_bytes(path.parent)
    if path.suffix.lower() == '.zip':
        try:
            with zipfile.ZipFile(path) as archive:
                candidates = [i for i in archive.infolist()
                              if i.filename.replace('\\', '/').split('/')[-1].lower() == 'ff2xmas.cca']
                if len(candidates) != 1 or candidates[0].file_size > MAX_INPUT:
                    raise project_index.InputError('ZIP must contain one full-version FF2xmas.cca (not the demo).')
                # Read one member in memory; never extract paths supplied by an archive.
                return archive.read(candidates[0])
        except (zipfile.BadZipFile, RuntimeError) as error:
            raise project_index.InputError('Cannot read this ZIP. Select your full-version FF2xmas.cca instead.') from error
    if path.stat().st_size > MAX_INPUT or path.suffix.lower() not in {'.cca', '.gam'}:
        raise project_index.InputError('Select the full-version FF2xmas.cca or funnyfurries.zip.')
    return path.read_bytes()


def import_copy(source, home, reader_source=None, progress=None):
    """progress(text, start, end) hears about each stage and the share of the whole
    it covers; extracting the pictures takes most of the ten-odd seconds."""
    step = progress or (lambda text, start, end: None)
    reader_source = reader_source or (ROOT if getattr(sys, 'frozen', False) else ROOT / 'reader')
    reader = project_index.load_reader(reader_source)
    step('Reading your copy…', 0.0, 0.03)
    raw = source_bytes(source)
    original = raw
    # The copy behind the current import: nothing to redo (Warpzone hands it over on every start).
    kept = Path(home) / KEPT
    current = selected(Path(home))
    if current and kept.is_file() and kept.read_bytes() == raw:
        return current
    try:
        game = reader.read(raw)
        if game.family != 'cnc':
            raise ValueError('not a Click & Create file')
        if game.protected:
            step('Unpacking the game data…', 0.03, 0.06)
            from klikback.core.tgf.unprotect import unprotect
            raw, _ = unprotect(game)
        step('Extracting pictures, sounds and levels…', 0.06, 0.78)
        manifest, files = export_project.research_bundle(reader, raw)
        sha = manifest['source']['sha256']
        target = Path(home) / ('arena-v9-' + sha)
        if target.exists():
            try:
                check_import(target)
            except (OSError, ValueError, KeyError, TypeError):
                # Preserve the damaged directory for inspection; publish a fresh atomic import.
                target = target.with_name(target.name + '-' + uuid.uuid4().hex[:8])
        # Scratch exports disappear even on failure. Only a complete atomic arena survives.
        Path(home).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.import-', dir=home) as scratch:
            bundle = export_project.save_bundle(manifest, files, Path(scratch))
            step('Building the arenas…', 0.78, 0.97)
            import_arena.import_arena(bundle, target)
        step('Checking the import…', 0.97, 1.0)
        check_import(target)
        keep_original(home, original)
        return target
    except (ValueError, KeyError, IndexError, struct.error) as error:
        raise project_index.InputError('This copy is unsupported or incomplete. Use the full FF2 Xmas game, not the demo.') from error


def keep_original(home, raw):
    """Keep the player's own copy beside its import, so a newer importer can
    redo the import without asking again. It never leaves this machine."""
    path = Path(home) / KEPT
    if path.exists() and path.read_bytes() == raw:
        return
    with tempfile.NamedTemporaryFile(dir=home, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(raw)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def check_import(target):
    report = json.loads((target / 'import.json').read_text())
    if report.get('importer') != 'arena-import/9' or not report.get('files'):
        raise project_index.InputError('Local import needs replacing. Choose your original copy again.')
    for name, digest in report['files'].items():
        if Path(name).name != name or '\\' in name or name in {'.', '..'}:
            raise project_index.InputError('Invalid local import filename.')
        path = target / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise project_index.InputError('Local import is damaged. Choose your original copy again.')


def save_selection(home, target):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=home, delete=False) as stream:
        temp = Path(stream.name)
        json.dump({'arena': target.name}, stream)
    try:
        os.replace(temp, home / 'selected.json')
    finally:
        temp.unlink(missing_ok=True)


def selected(home):
    try:
        name = json.loads((home / 'selected.json').read_text())['arena']
        if not isinstance(name, str) or Path(name).name != name or not name.startswith('arena-v9-'):
            return None
        target = home / name
        check_import(target)
        return target
    except (OSError, ValueError, KeyError, TypeError):
        return None


def report_fault(category):
    if os.environ.get('FF_NO_REPORT') == '1':
        return
    # A detached helper owns the network timeout; exiting the game never waits for it.
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command += [str(Path(__file__).resolve())]
    command += ['--deliver-fault', category]
    options = {'creationflags': 0x08000008} if os.name == 'nt' else {'start_new_session': True}
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **options)
    except OSError:
        pass


def deliver_fault(category):
    from urllib.request import Request, urlopen
    if category not in {'launcher', 'import', 'game'}:
        return
    # Fixed anonymous text only: no paths, usernames, original content or logs.
    payload = f'funny-furries/{VERSION} {platform.system()} {category} fault'.encode()
    try:
        with urlopen(Request(TOPIC, data=payload, method='POST'), timeout=4):
            pass
    except Exception:
        pass


def run_game(target, game_args):
    binary = PACKAGE / ('funny-furries.exe' if os.name == 'nt' else 'funny-furries')
    env = os.environ.copy()
    # PyInstaller's Python libraries must not be injected into a separate SDL process.
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
    else:
        env.pop('LD_LIBRARY_PATH', None)
    if os.name != 'nt':
        env['LD_LIBRARY_PATH'] = str(PACKAGE / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
    if os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    command = [str(binary)] + (['--data', str(target)] if target else []) + game_args
    # Explicit handles also reach GUI-subsystem executables on Windows.
    result = subprocess.run(command, env=env, stdout=sys.stdout, stderr=sys.stderr).returncode
    if result not in (0, 2):
        report_fault('game')
    return result


def with_progress(work, title='Funny Furries'):
    """Runs work(progress) and shows how far it is, so a long first start (or a
    re-import after an update) does not look like a launch that failed. Quick work
    returns before any window appears; without a display the stages go to stderr."""
    state = {'text': 'Preparing your game data…', 'start': 0.0, 'end': 0.05}
    outcome = []
    done = threading.Event()

    def progress(text, start, end):
        state.update(text=text, start=start, end=end)

    def run():
        try:
            outcome.append((True, work(progress)))
        except BaseException as error:
            outcome.append((False, error))
        finally:
            done.set()
    threading.Thread(target=run, daemon=True).start()
    if not done.wait(0.5):
        try:
            import tkinter as tk
            from tkinter import ttk
            root = tk.Tk()
        except Exception:
            root = None
        if root is None:
            shown = None
            while not done.wait(0.25):
                if state['text'] != shown:
                    shown = state['text']
                    print(f'Funny Furries: {shown}', file=sys.stderr, flush=True)
        else:
            root.title(title)
            root.geometry(f'520x170+{max(0, (root.winfo_screenwidth() - 520) // 2)}+{max(0, (root.winfo_screenheight() - 170) // 2)}')
            root.resizable(False, False)
            root.protocol('WM_DELETE_WINDOW', lambda: None)
            tk.Label(root, text='Preparing your game data', font=('sans-serif', 15, 'bold')).pack(pady=(20, 6))
            label = tk.StringVar(value=state['text'])
            tk.Label(root, textvariable=label).pack()
            bar = ttk.Progressbar(root, length=440, maximum=1000, mode='determinate')
            bar.pack(pady=14)
            tk.Label(root, text='This happens once, and again only after an update.', fg='#666').pack()

            def poll():
                if done.is_set():
                    root.destroy()
                    return
                label.set(state['text'])
                # Within a stage the bar eases toward its end, so it keeps moving
                # through the long extraction without ever claiming to be done.
                shown = max(bar['value'] / 1000, state['start'])
                bar['value'] = 1000 * (shown + (state['end'] - shown) * 0.025)
                root.after(100, poll)
            poll()
            root.mainloop()
            done.wait()
    ok, value = outcome[0]
    if not ok:
        raise value
    return value


def choose_and_import(home, reader_source):
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root = tk.Tk()
    root.title('Funny Furries — first start')
    root.geometry('620x330')
    root.resizable(False, False)
    result = [None]
    tk.Label(root, text='Funny Furries 2 Xmas', font=('sans-serif', 22, 'bold')).pack(pady=(24, 12))
    tk.Label(root, text='Choose your own full-version funnyfurries.zip or FF2xmas.cca.\n'
             'Your original stays untouched. Import happens once on this computer.\n'
             'No original game content is included or uploaded.', justify='center').pack()
    status = tk.StringVar(value='Two pads: A jump · X punch · B weapon · Y jetpack · Start play/pause')
    tk.Label(root, textvariable=status, wraplength=590).pack(pady=20)
    done = threading.Event()
    outcome = []
    latest = [None]

    def poll():
        if not done.is_set():
            if latest[0]:
                status.set(latest[0])
            root.after(100, poll)
            return
        button.config(state='normal')
        cancel.config(state='normal')
        root.protocol('WM_DELETE_WINDOW', root.destroy)
        if isinstance(outcome[0], Exception):
            error = outcome[0]
            if isinstance(error, (project_index.InputError, FileNotFoundError, PermissionError)):
                messagebox.showerror('Import could not finish', str(error))
            else:
                report_fault('import')
                messagebox.showerror('Import failed', 'Unexpected import failure. Please report this problem. Your original was not changed.')
            status.set('Choose another full-version copy to try again.')
        else:
            result[0] = outcome[0]
            root.destroy()

    def choose():
        path = filedialog.askopenfilename(title='Your own Funny Furries 2 Xmas copy',
                filetypes=[('FF2 Xmas copy', '*.zip *.cca *.CCA *.exe'), ('All files', '*')])
        if not path:
            return
        button.config(state='disabled')
        cancel.config(state='disabled')
        status.set('Importing your copy… This may take a minute.')
        root.protocol('WM_DELETE_WINDOW', lambda: None)
        done.clear()
        outcome.clear()

        def stage(text, start, end):
            # Tk belongs to this thread's caller: poll() shows the latest stage.
            latest[0] = f'{text} ({int(start * 100)} %)'

        def work():
            try:
                target = import_copy(path, home, reader_source, stage)
                save_selection(home, target)
                outcome.append(target)
            except Exception as error:
                outcome.append(error)
            finally:
                done.set()
        threading.Thread(target=work, daemon=True).start()
        root.after(100, poll)

    button = tk.Button(root, text='Choose original copy and play', command=choose, padx=18, pady=9)
    button.pack()
    cancel = tk.Button(root, text='Cancel', command=root.destroy)
    cancel.pack(pady=8)
    root.mainloop()
    return result[0]


def handed_over(source, home, reader_source):
    try:
        target = with_progress(lambda progress: import_copy(source, home, reader_source, progress))
        save_selection(home, target)
        return target
    except (project_index.InputError, OSError) as error:
        print(f'Could not use the copy Warpzone found ({source}): {error}', file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-copy', type=Path)
    parser.add_argument('--reader-source', type=Path)
    parser.add_argument('--home', type=Path, default=data_home())
    parser.add_argument('--import-only', action='store_true')
    parser.add_argument('--reimport', action='store_true')
    parser.add_argument('--practice', action='store_true')
    parser.add_argument('--deliver-fault', choices=['launcher', 'import', 'game'])
    args, game_args = parser.parse_known_args()
    if args.deliver_fault:
        deliver_fault(args.deliver_fault)
        return 0
    try:
        target = None if args.reimport else selected(args.home)
        if not target and not args.reimport and not args.import_copy and (args.home / KEPT).is_file():
            # An update changed the importer: redo it from the kept copy, silently.
            try:
                target = with_progress(lambda progress: import_copy(args.home / KEPT, args.home, args.reader_source, progress))
                save_selection(args.home, target)
            except project_index.InputError:
                target = None
        found = os.environ.get(WARPZONE_DATA)
        if args.import_copy and not found:
            target = with_progress(lambda progress: import_copy(args.import_copy, args.home, args.reader_source, progress))
            save_selection(args.home, target)
        elif args.import_copy or (found and not target and not args.reimport and not args.practice):
            # Under Warpzone a copy it found but we cannot use must not stop the game:
            # say why and fall back to asking, as a first start without Warpzone would.
            target = handed_over(args.import_copy or Path(found), args.home, args.reader_source) or target
        if not target and not args.practice:
            target = choose_and_import(args.home, args.reader_source)
            if target is None:
                return 0
        if args.import_only:
            return 0
        return run_game(None if args.practice else target, game_args)
    except (project_index.InputError, FileNotFoundError, PermissionError) as error:
        print(f'Cannot start: {error}', file=sys.stderr)
        return 2
    except Exception:
        report_fault('launcher')
        print('Unexpected launcher failure. Please report this problem.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
