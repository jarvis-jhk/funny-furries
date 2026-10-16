"""First-start failure recovery, archive handling and optional real-copy import."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from tools import launcher


class LauncherTests(unittest.TestCase):
    def test_archive_reads_one_member_without_extracting_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'copy.zip'
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr('../outside', b'never extract')
                stream.writestr('folder/FF2xmas.cca', b'player bytes')
            self.assertEqual(launcher.source_bytes(archive), b'player bytes')
            self.assertFalse((Path(directory).parent / 'outside').exists())
            with zipfile.ZipFile(archive, 'a') as stream:
                stream.writestr('other/ff2xmas.cca', b'ambiguous')
            with self.assertRaises(launcher.project_index.InputError):
                launcher.source_bytes(archive)

    def test_selection_refuses_escape_and_damaged_import(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'selected.json').write_text('{"arena":"../outside"}')
            self.assertIsNone(launcher.selected(home))
            arena = home / 'arena-v5-test'
            arena.mkdir()
            (arena / 'arena.ff').write_bytes(b'local')
            (arena / 'import.json').write_text('{"importer":"arena-import/5","files":{"arena.ff":"' + hashlib.sha256(b'local').hexdigest() + '"}}')
            launcher.save_selection(home, arena)
            self.assertEqual(launcher.selected(home), arena)
            (arena / 'arena.ff').write_bytes(b'damaged')
            self.assertIsNone(launcher.selected(home))

    def test_fault_reports_only_runtime_exit_and_is_nonblocking(self):
        with patch.object(launcher.subprocess, 'run') as run, patch.object(launcher, 'report_fault') as report:
            for status in (0, 2):
                run.return_value.returncode = status
                launcher.run_game(None, [])
            report.assert_not_called()
            run.return_value.returncode = -11
            launcher.run_game(None, [])
            report.assert_called_once_with('game')
            self.assertIs(run.call_args.kwargs['stdout'], launcher.sys.stdout)
            self.assertIs(run.call_args.kwargs['stderr'], launcher.sys.stderr)
        with patch.object(launcher.subprocess, 'Popen') as popen, patch.dict(os.environ, {'FF_NO_REPORT': '1'}):
            launcher.report_fault('game')
            popen.assert_not_called()

    def test_warpzone_found_copy_is_imported_without_asking(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            found = home / 'Downloads' / 'funnyfurries.zip'
            arena = home / 'arena-v5-x'
            with patch.dict(os.environ, {launcher.WARPZONE_DATA: str(found)}), \
                    patch.object(launcher, 'selected', return_value=None), \
                    patch.object(launcher, 'import_copy', return_value=arena) as copy, \
                    patch.object(launcher, 'save_selection') as save, \
                    patch.object(launcher, 'choose_and_import') as ask, \
                    patch.object(launcher, 'run_game', return_value=0) as run, \
                    patch.object(launcher.sys, 'argv', ['launcher', '--home', str(home)]):
                self.assertEqual(launcher.main(), 0)
                copy.assert_called_once_with(found, home, None)
                save.assert_called_once_with(home, arena)
                ask.assert_not_called()
                run.assert_called_once_with(arena, [])
                # The launcher also passes import_args until selected.json exists: same copy, once.
                copy.reset_mock()
                with patch.object(launcher.sys, 'argv', ['launcher', '--home', str(home), '--import-copy', str(found)]):
                    self.assertEqual(launcher.main(), 0)
                copy.assert_called_once_with(found, home, None)
                ask.assert_not_called()

    def test_warpzone_copy_is_not_reimported_once_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            arena = home / 'arena-v5-x'
            with patch.dict(os.environ, {launcher.WARPZONE_DATA: str(home / 'FF2xmas.cca')}), \
                    patch.object(launcher, 'selected', return_value=arena), \
                    patch.object(launcher, 'import_copy') as copy, \
                    patch.object(launcher, 'choose_and_import') as ask, \
                    patch.object(launcher, 'run_game', return_value=0) as run, \
                    patch.object(launcher.sys, 'argv', ['launcher', '--home', str(home)]):
                self.assertEqual(launcher.main(), 0)
            copy.assert_not_called()
            ask.assert_not_called()
            run.assert_called_once_with(arena, [])

    def test_unusable_warpzone_copy_falls_back_to_asking(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            demo = home / 'funnyfurries.zip'
            with zipfile.ZipFile(demo, 'w') as stream:
                stream.writestr('readme.txt', b'demo')
            arena = home / 'arena-v5-chosen'
            for argv in (['launcher', '--home', str(home)],
                         ['launcher', '--home', str(home), '--import-copy', str(demo)]):
                with patch.dict(os.environ, {launcher.WARPZONE_DATA: str(demo)}), \
                        patch.object(launcher, 'choose_and_import', return_value=arena) as ask, \
                        patch.object(launcher, 'run_game', return_value=0) as run, \
                        patch.object(launcher.sys, 'argv', argv):
                    self.assertEqual(launcher.main(), 0)
                ask.assert_called_once_with(home, None)
                run.assert_called_once_with(arena, [])
            # Without Warpzone an explicit bad --import-copy still fails loudly.
            with patch.dict(os.environ, {}, clear=False), patch.object(launcher, 'choose_and_import') as ask, \
                    patch.object(launcher.sys, 'argv', ['launcher', '--home', str(home), '--import-copy', str(demo)]):
                os.environ.pop(launcher.WARPZONE_DATA, None)
                self.assertEqual(launcher.main(), 2)
            ask.assert_not_called()

    @unittest.skipUnless(os.environ.get('FF_TEST_COPY') and os.environ.get('FF_KLIKBACK_SRC'), 'local original copy optional')
    def test_real_protected_copy_first_start_repeat_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = Path(os.environ['FF_TEST_COPY'])
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            target = launcher.import_copy(source, home, Path(os.environ['FF_KLIKBACK_SRC']))
            launcher.save_selection(home, target)
            self.assertEqual(launcher.selected(home), target)
            self.assertEqual(launcher.import_copy(source, home, Path(os.environ['FF_KLIKBACK_SRC'])), target)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertTrue((target / 'arena.ff').is_file())
            self.assertFalse(list(home.glob('.import-*')))
            self.assertEqual(len(list(home.glob('arena-v5-*'))), 1)
            (target / 'arena.ff').write_bytes(b'damaged')
            self.assertIsNone(launcher.selected(home))
            repaired = launcher.import_copy(source, home, Path(os.environ['FF_KLIKBACK_SRC']))
            self.assertNotEqual(repaired, target)
            launcher.save_selection(home, repaired)
            self.assertEqual(launcher.selected(home), repaired)
            self.assertEqual((target / 'arena.ff').read_bytes(), b'damaged')
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
