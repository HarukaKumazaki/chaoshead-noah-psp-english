"""In-place ISO9660 file replacer for PSP UMD images.

Usage: iso_patch.py base.iso out.iso ISO/PATH=localfile [...]
A replacement that fits its original extent (up to the next used sector) is written
in place; a larger one is appended at the end of the image. Directory records (both
LE and BE fields) and the PVD volume size are updated.
"""
import struct, sys, shutil, os

SECTOR = 2048


def read_dir(f, lba, size):
    f.seek(lba * SECTOR)
    data = f.read(size)
    recs = []
    p = 0
    while p < len(data):
        ln = data[p]
        if ln == 0:
            p = (p // SECTOR + 1) * SECTOR
            continue
        ext, sz = struct.unpack_from('<I', data, p + 2)[0], struct.unpack_from('<I', data, p + 10)[0]
        flags = data[p + 25]
        nl = data[p + 32]
        name = data[p + 33:p + 33 + nl]
        recs.append((lba * SECTOR + p, ext, sz, flags, name))
        p += ln
    return recs


def walk(f):
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    root = pvd[156:156 + 34]
    rext, rsz = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
    out = {}
    stack = [('', rext, rsz)]
    while stack:
        path, ext, sz = stack.pop()
        for pos, e, s, fl, name in read_dir(f, ext, sz):
            if name in (b'\0', b'\1'):
                continue
            nm = name.decode('ascii').split(';')[0]
            full = path + '/' + nm
            if fl & 2:
                stack.append((full, e, s))
            else:
                out[full.upper()] = (pos, e, s)
    return out


def main(base, out, repl):
    if os.path.abspath(base) != os.path.abspath(out):
        shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        files = walk(f)
        f.seek(0, 2)
        end_sector = (f.tell() + SECTOR - 1) // SECTOR
        starts = sorted(e for _, e, _ in files.values())
        for isopath, local in repl:
            pos, ext, size = files['/' + isopath.strip('/').upper()]
            data = open(local, 'rb').read()
            nxt = min([s for s in starts if s > ext] + [end_sector])
            room = (nxt - ext) * SECTOR
            if len(data) <= room:
                new_ext = ext
            else:
                new_ext = end_sector
                end_sector += (len(data) + SECTOR - 1) // SECTOR
            f.seek(new_ext * SECTOR)
            f.write(data)
            f.write(b'\0' * (-len(data) % SECTOR))
            if new_ext == ext and len(data) < size:
                f.write(b'\0' * max(0, (size - len(data)) - (-len(data) % SECTOR)))
            f.seek(pos + 2); f.write(struct.pack('<I', new_ext) + struct.pack('>I', new_ext))
            f.seek(pos + 10); f.write(struct.pack('<I', len(data)) + struct.pack('>I', len(data)))
            print('%-40s %10d -> %10d  %s' % (isopath, size, len(data), 'in place' if new_ext == ext else 'moved to %d' % new_ext))
        f.seek(0, 2)
        total = (f.tell() + SECTOR - 1) // SECTOR
        f.truncate(total * SECTOR)
        f.seek(16 * SECTOR + 80); f.write(struct.pack('<I', total) + struct.pack('>I', total))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], [a.split('=', 1) for a in sys.argv[3:]])
