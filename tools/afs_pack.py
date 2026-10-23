"""Recursive AFS packer, inverse of afs_unpack.py.
Usage: afs_pack.py srcdir out.afs [overlaydir [original.afs]]
With original.afs, top-level children with nothing in the overlay are copied verbatim (fast).
Files found at the same relative path under overlaydir replace the originals."""
import struct, sys, os, json

ALIGN = 0x800


def pad(b, a=ALIGN):
    return b + b'\0' * (-len(b) % a)


def pack(d, ov=None, orig=None):
    man = json.load(open(os.path.join(d, '_manifest.json')))
    files = man['files']
    n = len(files)
    blobs = []
    oents = None
    if orig is not None:
        on = struct.unpack_from('<I', orig, 4)[0]
        oents = [struct.unpack_from('<II', orig, 8 + 8 * i) for i in range(on)]
    for idx, it in enumerate(files):
        fn = it.get('file', it['name'])
        untouched = not (ov and os.path.exists(os.path.join(ov, fn + ('.d' if it.get('afs') else ''))))
        if oents is not None and untouched:
            o, sz = oents[idx]
            blobs.append(orig[o:o + sz])
            continue
        if it.get('afs'):
            blobs.append(pack(os.path.join(d, fn + '.d'), ov and os.path.join(ov, fn + '.d')))
        else:
            src = os.path.join(ov, fn) if ov and os.path.exists(os.path.join(ov, fn)) else os.path.join(d, fn)
            blobs.append(open(src, 'rb').read())
    hdr_len = 8 + 8 * n + 8
    off = max(ALIGN, (hdr_len + ALIGN - 1) // ALIGN * ALIGN)
    ents = []
    body = bytearray()
    for b in blobs:
        ents.append((off + len(body), len(b)))
        body += pad(b)
    name_off = off + len(body) if man['hasnames'] else 0
    names = bytearray()
    if man['hasnames']:
        for it, b in zip(files, blobs):
            meta = bytes.fromhex(it['meta'])  # not a size field in this game; keep as-is
            names += it['name'].encode('ascii').ljust(32, b'\0') + meta
    out = bytearray(b'AFS\0' + struct.pack('<I', n))
    for o, s in ents:
        out += struct.pack('<II', o, s)
    out += struct.pack('<II', name_off, len(names))
    out = pad(out)
    out += body
    out += names
    return bytes(pad(out))


if __name__ == '__main__':
    orig = open(sys.argv[4], 'rb').read() if len(sys.argv) > 4 else None
    data = pack(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None, orig)
    open(sys.argv[2], 'wb').write(data)
    print(sys.argv[2], len(data))
