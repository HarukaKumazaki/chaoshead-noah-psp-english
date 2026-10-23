"""Assemble the release folder and zip (what players download).

Usage: package.py VERSION      (after build.py and makepatch.py ... release)

  dist/CHN-PSP-English-VERSION/      patchers + patch + README.txt
  dist/CHN-PSP-English-VERSION.zip
"""
import sys, os, shutil, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
PATCHERS = ['Patch-Windows.bat', 'patcher.ps1', 'patch-linux.sh']
PATCH = ['ChaosHeadNoah_PSP_EN.patch.bin', 'ChaosHeadNoah_PSP_EN.patch.txt']


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def eol(path, nl):
    b = open(path, 'rb').read().replace(b'\r\n', b'\n')
    open(path, 'wb').write(b.replace(b'\n', nl))


def main():
    version = sys.argv[1]
    name = 'CHN-PSP-English-' + version
    rel = os.path.join(DIST, name)
    shutil.rmtree(rel, ignore_errors=True)
    for f in PATCHERS:
        copy(os.path.join(ROOT, 'patcher', f), os.path.join(rel, f))
    for f in PATCH:
        copy(os.path.join(ROOT, 'release', f), os.path.join(rel, f))
    copy(os.path.join(ROOT, 'INSTALL.md'), os.path.join(rel, 'README.txt'))
    eol(os.path.join(rel, 'patch-linux.sh'), b'\n')          # shell scripts need Unix line endings
    eol(os.path.join(rel, 'Patch-Windows.bat'), b'\r\n')
    eol(os.path.join(rel, 'README.txt'), b'\r\n')
    z = os.path.join(DIST, name + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in sorted(os.listdir(rel)):
            info = zipfile.ZipInfo(name + '/' + f)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if f.endswith('.sh') else 0o644) << 16
            zf.writestr(info, open(os.path.join(rel, f), 'rb').read())
    print('release ->', z, '%.1f MB' % (os.path.getsize(z) / 1e6))


if __name__ == '__main__':
    main()
