"""Build local distributions using the already installed, pinned setuptools."""

import subprocess
import sys
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__:
    from .check_release import ROOT, path_problem, source_files, text_findings, png_findings
else:
    from check_release import ROOT, path_problem, source_files, text_findings, png_findings
from controlomics.storage import write_bytes_atomic


def main():
    # Build from a reviewed public inventory, never from this machine's private
    # working directory or stale egg-info manifest.
    revision = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'rev-parse', 'HEAD'],
                              cwd=ROOT, capture_output=True, text=True, timeout=10)
    if revision.returncode == 0:
        print('Local source base revision: ' + revision.stdout.strip(), flush=True)
    with TemporaryDirectory(prefix='controlomics_public_build_') as temporary:
        public = Path(temporary)/'source'
        public.mkdir()
        names = source_files()
        for name in names:
            original = ROOT/name
            if path_problem(name) or original.is_symlink() or not original.resolve().is_relative_to(ROOT):
                raise ValueError('public build inventory contains an excluded file')
            raw = original.read_bytes()
            try:
                findings = text_findings(raw.decode('utf-8'))
            except UnicodeDecodeError:
                findings = png_findings(raw) if original.suffix == '.png' else [{'rule': 'unreviewed_binary'}]
            if findings:
                raise ValueError('public build inventory failed privacy screening')
            destination = public/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        script = 'from setuptools.build_meta import build_sdist, build_wheel; build_sdist("dist"); build_wheel("dist")'
        print('Building from ' + str(len(names)) + ' reviewed public files.', flush=True)
        result = subprocess.run([sys.executable, '-c', script], cwd=public, capture_output=True, text=True, timeout=300)
        if result.returncode:
            raise RuntimeError('distribution build failed; no package was published')
        output = ROOT/'dist'
        output.mkdir(exist_ok=True)
        for package in (public/'dist').iterdir():
            if package.suffix == '.whl':
                with zipfile.ZipFile(package) as archive:
                    for member in archive.infolist():
                        if member.filename.startswith('controlomics/'):
                            if path_problem(member.filename):
                                raise ValueError('wheel contains an excluded file')
                        elif '.dist-info/' not in member.filename:
                            raise ValueError('wheel contains an unexpected package')
                write_bytes_atomic(output/package.name, package.read_bytes())
            elif package.name.endswith('.tar.gz'):
                # Standard tar creation can retain the build account. Normalize
                # archive ownership while preserving source bytes and paths.
                normalized = BytesIO()
                with tarfile.open(package, 'r:gz') as source, tarfile.open(fileobj=normalized, mode='w:gz', format=tarfile.PAX_FORMAT) as target:
                    for member in source.getmembers():
                        if not (member.isfile() or member.isdir()) or member.name.startswith('/') or '..' in Path(member.name).parts:
                            raise ValueError('source archive contains an unsafe member')
                        relative = '/'.join(member.name.split('/')[1:])
                        generated_metadata = relative == 'src/controlomics.egg-info' or relative.startswith('src/controlomics.egg-info/')
                        if generated_metadata and member.isfile() and Path(relative).name not in {'PKG-INFO', 'SOURCES.txt', 'requires.txt', 'top_level.txt', 'dependency_links.txt', 'entry_points.txt'}:
                            raise ValueError('source archive contains unexpected generated metadata')
                        if relative and not generated_metadata and path_problem(relative):
                            raise ValueError('source archive contains an excluded file')
                        raw = source.extractfile(member).read() if member.isfile() else None
                        member.uid = member.gid = 0
                        member.uname = member.gname = ''
                        member.pax_headers = {key: value for key, value in member.pax_headers.items() if key in {'path', 'mtime'}}
                        target.addfile(member, BytesIO(raw) if raw is not None else None)
                write_bytes_atomic(output/package.name, normalized.getvalue())
            else:
                raise ValueError('unexpected build output')
            print('Built local distribution: ' + package.name)


if __name__ == '__main__':
    main()
