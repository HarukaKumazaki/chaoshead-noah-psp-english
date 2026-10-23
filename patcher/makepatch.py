"""Build the patch from the original and the translated ISO (same size).

Usage: makepatch.py ORIGINAL.iso ENGLISH.iso OUTDIR [OTHER_DUMP.iso ...]
OTHER_DUMP: other dumps of the same Japanese game (e.g. the PSN release). Each is accepted when the patch
never reads from a sector where it differs from ORIGINAL; its own result checksum is recorded.

Rebuilding the AFS archives moves most files, so the patch describes the English ISO in 2048-byte
sectors: sectors found anywhere in the original ISO are copied from it, only new data is shipped.
Everything goes into one self-contained file, ChaosHeadNoah_PSP_EN.dat, readable with plain shell
tools (dd / PowerShell). Patching needs only this file and the Japanese ISO.

  sectors 0-127 (256 KiB)  ASCII index, ended by a line "end", padded with newlines:
      size <bytes>                  size of both ISOs
      source_sha256 <hex>           original Japanese ISO
      result_sha256 <hex>           patched English ISO
      variant <source sha256> <result sha256>   another accepted Japanese dump and its result
      patched <sha256> <version>               an already-patched English ISO (clear error message)
      file <sha256> <iso sector> <bytes> <path>  a file the patch writes: checked one by one after patching
      copy <iso sector> <sector in the original ISO> <count>
      block <iso sector> <data sector> <count>
  sector 128 onwards       the new sectors, back to back (data sector 0 = file sector 128)
Patchers start from a copy of the original, then apply the lines (copies read the original file).
"""
import sys, os, struct, hashlib

SECTOR = 2048
CHUNK = SECTOR * 8192
NAME = 'ChaosHeadNoah_PSP_EN.dat'
HEADER = 128                    # index sectors at the start of the .dat


def h(b):
    return hashlib.blake2b(b, digest_size=16).digest()


def sectors(path):
    with open(path, 'rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                return
            for k in range(0, len(b), SECTOR):
                yield b[k:k + SECTOR]

def iso_files(path):
    """(path, first sector, bytes) of every file in an ISO9660 image"""
    out = []
    with open(path, 'rb') as f:
        def walk(lba, size, prefix):
            f.seek(lba * SECTOR); data = f.read(size); p = 0
            while p < len(data):
                n = data[p]
                if n == 0:                                       # records never cross a sector
                    p = (p // SECTOR + 1) * SECTOR
                    continue
                r = data[p:p + n]; p += n
                ext, length = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0]
                name = r[33:33 + r[32]]
                if name in (b'\x00', b'\x01'):
                    continue
                name = name.decode('ascii').split(';')[0]
                if r[25] & 2:
                    walk(ext, length, prefix + name + '/')
                else:
                    out.append((prefix + name, ext, length))
        f.seek(16 * SECTOR); root = f.read(SECTOR)[156:190]
        walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return out


class FileHashes:
    """sha256 of the given files, fed with the image sector by sector"""
    def __init__(self, files):
        self.at = {}
        for path, lba, size in files:
            for k in range((size + SECTOR - 1) // SECTOR):
                self.at[lba + k] = (path, size - k * SECTOR)
        self.sha = {path: hashlib.sha256() for path, _, _ in files}

    def update(self, i, sec):
        if i in self.at:
            path, left = self.at[i]
            self.sha[path].update(sec[:left])

    def digests(self):
        return {p: s.hexdigest() for p, s in self.sha.items()}


# checksums of earlier English releases: patchers tell the user to use the Japanese ISO instead
PATCHED = {'6e3c9dd58a74b3305439d54ca401eb9c5d369a4f544267618ba9da2f4bfcbd26': '1.0.0',
           'b9213b0beb0f0ceb46b3ae6a4e3b5a476292cd62049d10e40b91cd40aff234a1': '1.0.1'}


def variants(src, others, ops, part, files, want):
    """for each other dump: check it differs from src only where the patch writes and never where it
    reads, apply the patch to it (in memory, sector by sector) and return (source sha, result sha)"""
    out = []
    for path in others:
        if os.path.getsize(path) != os.path.getsize(src):
            raise SystemExit('%s: different size' % path)
        diff = set(i for i, (a, b) in enumerate(zip(sectors(src), sectors(path))) if a != b)
        for kind, d, s_, n in ops:
            if kind == 'copy' and diff & set(range(s_, s_ + n)):
                raise SystemExit('%s: the patch reads sectors that differ in this dump' % path)
        write = {}
        for kind, d, s_, n in ops:
            for k in range(n):
                write[d + k] = (kind, s_ + k)
        sha_s, sha_r, fh = hashlib.sha256(), hashlib.sha256(), FileHashes(files)
        srcf = open(path, 'rb'); binf = open(part, 'rb')
        for i, sec in enumerate(sectors(path)):
            sha_s.update(sec)
            if i in write:
                kind, k = write[i]
                f = srcf if kind == 'copy' else binf
                f.seek(k * SECTOR); sec = f.read(SECTOR)
            sha_r.update(sec); fh.update(i, sec)
        srcf.close(); binf.close()
        if fh.digests() != want:                                 # patchers check one file list for all dumps
            raise SystemExit('%s: patched files differ from the main dump' % path)
        out.append((sha_s.hexdigest(), sha_r.hexdigest()))
        print('variant ok: %s (%d sectors differ, none read by the patch)' % (os.path.basename(path), len(diff)))
    return out


def main():
    src, dst, outdir = sys.argv[1:4]
    size = os.path.getsize(src)
    if os.path.getsize(dst) != size or size % SECTOR:
        raise SystemExit('ISOs must be the same size (a whole number of sectors)')
    print('indexing the original...')
    first, hashes, sha_src = {}, [], hashlib.sha256()
    for i, s in enumerate(sectors(src)):
        sha_src.update(s)
        d = h(s)
        hashes.append(d)
        first.setdefault(d, i)
    print('matching...')
    os.makedirs(outdir, exist_ok=True)
    ops = []            # [kind, dst start, src/data start, count]
    sha_dst, nbin = hashlib.sha256(), 0
    part = os.path.join(outdir, NAME + '.part')
    with open(part, 'wb') as binf:
        for i, s in enumerate(sectors(dst)):
            sha_dst.update(s)
            d = h(s)
            if d == hashes[i]:
                continue                                         # unchanged in place
            last = ops[-1] if ops else None
            if last and last[0] == 'copy' and last[1] + last[3] == i and hashes[last[2] + last[3]] == d:
                last[3] += 1                                     # continues the previous copy run
            elif d in first:
                ops.append(['copy', i, first[d], 1])
            elif last and last[0] == 'block' and last[1] + last[3] == i:
                binf.write(s); nbin += 1; last[3] += 1
            else:
                binf.write(s); ops.append(['block', i, nbin, 1]); nbin += 1
    written = set()
    for kind, d, s_, n in ops:
        written.update(range(d, d + n))
    files = [f for f in iso_files(dst)
             if written & set(range(f[1], f[1] + (f[2] + SECTOR - 1) // SECTOR))]
    fh = FileHashes(files)
    for i, s in enumerate(sectors(dst)):
        fh.update(i, s)
    want = fh.digests()
    lines = ['size %d' % size, 'source_sha256 %s' % sha_src.hexdigest(), 'result_sha256 %s' % sha_dst.hexdigest()]
    lines += ['variant %s %s' % v for v in variants(src, sys.argv[4:], ops, part, files, want)]
    lines += ['patched %s %s' % kv for kv in PATCHED.items()] + ['patched %s 1.0.2+' % sha_dst.hexdigest()]
    lines += ['file %s %d %d %s' % (want[p], lba, size, p) for p, lba, size in files]
    lines += ['%s %d %d %d' % tuple(o) for o in ops]
    index = ('\n'.join(lines + ['end']) + '\n').encode('ascii')
    if len(index) > HEADER * SECTOR:
        raise SystemExit('index does not fit the %d-sector header' % HEADER)
    with open(os.path.join(outdir, NAME), 'wb') as out, open(part, 'rb') as binf:
        out.write(index.ljust(HEADER * SECTOR, b'\n'))
        while True:
            b = binf.read(CHUNK)
            if not b:
                break
            out.write(b)
    os.remove(part)
    print('%d patched files listed for checking' % len(files))
    print('%d copy runs, %d new-data runs, %.1f MB new data -> %s' % (
        sum(o[0] == 'copy' for o in ops), sum(o[0] == 'block' for o in ops), nbin * SECTOR / 1e6,
        os.path.join(outdir, NAME)))


if __name__ == '__main__':
    main()
