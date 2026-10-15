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
        with patch.object(launcher.subprocess, 'Popen') as popen, patch.dict(os.environ, {'FF_NO_REPORT': '1'}):
            launcher.report_fault('game')
            popen.assert_not_called()

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
