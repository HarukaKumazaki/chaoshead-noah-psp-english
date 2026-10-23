"""Prepare the build inputs from the Japanese ISO and the Steam game (run once before build.py).

Usage: setup.py "Chaos;Head Noah (Japan).iso" "STEAM/CHAOS;HEAD NOAH"

  iso/        files of the Japanese ISO (read-only reference)
  unpacked/   DATA0.AFS / DATA1.AFS unpacked (nested AFS archives become NAME.d folders)
  steam/      text and pictures from the Steam release (Data/*.cpk) and the CoZ patch
              (languagebarrier/c0*.cpk)

The decrypted EBOOT (work/eboot/EBOOT_dec.ELF) is made with PPSSPP; see BUILDING.md.
"""
import sys, os, struct, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
SECTOR = 2048
STEAM_CPK = ['bg_eng', 'system_eng']                                         # Data/
COZ_CPK = ['mes00', 'mes01', 'c0data', 'c0mes00', 'c0mes01', 'c0script']     # languagebarrier/ (CoZ)


def extract_iso(iso, out):
    """plain ISO9660 reader (PSP UMD images have no Joliet/Rock Ridge)"""
    with open(iso, 'rb') as f:
        def read(sec, n):
            f.seek(sec * SECTOR)
            return f.read(n)
        pvd = read(16, SECTOR)
        assert pvd[1:6] == b'CD001', 'not an ISO9660 image'

        def walk(rec, path):
            sec, size = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
            data = read(sec, size)
            pos = 0
            while pos < len(data):
                ln = data[pos]
                if ln == 0:                                  # records never cross a sector
                    pos = (pos // SECTOR + 1) * SECTOR
                    continue
                r = data[pos:pos + ln]
                name = r[33:33 + r[32]]
                pos += ln
                if name in (b'\0', b'\1'):
                    continue
                name = name.decode('ascii').split(';')[0]
                dst = os.path.join(path, name)
                if r[25] & 2:
                    os.makedirs(dst, exist_ok=True)
                    walk(r, dst)
                else:
                    fsec, fsize = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0]
                    with open(dst, 'wb') as o:
                        f.seek(fsec * SECTOR)
                        left = fsize
                        while left:
                            chunk = f.read(min(left, 1 << 24))
                            o.write(chunk)
                            left -= len(chunk)
        os.makedirs(out, exist_ok=True)
        walk(pvd[156:156 + 34], out)


def run(*a):
    print('>', ' '.join(os.path.basename(x) for x in a[:1]), *a[1:], flush=True)
    subprocess.check_call([sys.executable] + list(a), cwd=ROOT)


def main():
    iso, steam = sys.argv[1], sys.argv[2]
    print('extracting the ISO...')
    extract_iso(iso, os.path.join(ROOT, 'iso'))
    usr = os.path.join(ROOT, 'iso', 'PSP_GAME', 'USRDIR')
    for a in ('DATA0', 'DATA1'):
        run(os.path.join(T, 'afs_unpack.py'), os.path.join(usr, a + '.AFS'), os.path.join(ROOT, 'unpacked', a))
    for name in STEAM_CPK:
        run(os.path.join(T, 'cpk_extract.py'), os.path.join(steam, 'Data', name + '.cpk'),
            os.path.join(ROOT, 'steam', name))
    for name in COZ_CPK:
        run(os.path.join(T, 'cpk_extract.py'), os.path.join(steam, 'languagebarrier', name + '.cpk'),
            os.path.join(ROOT, 'steam', name))
    print('done. Next: dump the decrypted EBOOT (BUILDING.md), then run build.py')


if __name__ == '__main__':
    main()
