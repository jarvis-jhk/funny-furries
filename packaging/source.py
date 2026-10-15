"""Package only committed source and pinned reader; never enumerate local export/orig files."""
from pathlib import Path
import subprocess
import tarfile

out = Path('build/artifacts')
out.mkdir(exist_ok=True)
subprocess.run(['git', 'archive', '--format=tar', '--prefix=funny-furries-source/',
                '-o', 'build/our-source.tar', 'HEAD'], check=True)
subprocess.run(['git', '-C', 'build/klikback', 'archive', '--format=tar',
                '--prefix=funny-furries-source/build/klikback/',
                '-o', str(Path('build/reader-source.tar').resolve()),
                '6e178b9470206f71871417dec852fbfa24cd01b9'], check=True)
with tarfile.open(out / 'funny-furries-source.tar.gz', 'w:gz') as target:
    for archive in ('build/our-source.tar', 'build/reader-source.tar'):
        with tarfile.open(archive) as source:
            for info in source:
                target.addfile(info, source.extractfile(info) if info.isfile() else None)

    for name in ('SDL2-2.30.12.tar.gz', 'SDL2_image-2.8.8.tar.gz', 'SDL2_mixer-2.8.1.tar.gz'):
        target.add(Path('build/media-source') / name, arcname='funny-furries-source/build/media-source/' + name)
