"""Run on the target OS with pinned KlikBack source in build/klikback."""
from pathlib import Path
import shutil
import importlib.metadata
import sysconfig
import subprocess
import sys

reader = Path('build/klikback/src').resolve()
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                '--name', 'Play-Funny-Furries', '--onedir',
                '--paths', str(reader), '--paths', str(Path('.').resolve()),
                '--add-data', f'{reader / "klikback"}:klikback',
                '--hidden-import', 'klikback.core.tgf.format',
                '--hidden-import', 'klikback.core.tgf.unprotect',
                '--distpath', 'build/frozen', '--workpath', 'build/freeze',
                '--specpath', 'build', 'tools/launcher.py'], check=True)
package = Path('build/package/funny-furries')
if package.exists():
    shutil.rmtree(package)
package.mkdir(parents=True)
shutil.copytree('build/frozen/Play-Funny-Furries', package, dirs_exist_ok=True)
for name in ('COPYING', 'THIRD_PARTY.md', 'README.md'):
    shutil.copy2(name, package)
shutil.copy2('docs/RELEASE.md', package / 'PLAYING.txt')
licenses = package / 'licenses'
licenses.mkdir(exist_ok=True)
shutil.copy2('build/klikback/LICENSE', licenses / 'KlikBack.txt')
for library in ('SDL2-2.30.12', 'SDL2_image-2.8.8', 'SDL2_mixer-2.8.1'):
    shutil.copy2(Path('build/media-source') / library / 'LICENSE.txt', licenses / (library + '.txt'))
# CPython Windows distributions and Unix source installs ship LICENSE.txt.
for path in (Path(sys.base_prefix) / 'LICENSE.txt', Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt'):
    if path.is_file():
        shutil.copy2(path, licenses / 'Python.txt')
        break
dist = importlib.metadata.distribution('pyinstaller')
for file in dist.files:
    if str(file).endswith('licenses/COPYING.txt'):
        shutil.copy2(dist.locate_file(file), licenses / 'PyInstaller.txt')
