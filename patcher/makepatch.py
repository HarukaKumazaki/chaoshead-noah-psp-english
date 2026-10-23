"""Build the patch from the original and the translated ISO (same size).

Usage: makepatch.py ORIGINAL.iso ENGLISH.iso OUTDIR

Rebuilding the AFS archives moves most files, so the patch describes the English ISO in 2048-byte
sectors: sectors found anywhere in the original ISO are copied from it, only new data is shipped.
Two files, readable by plain shell tools (dd / PowerShell) with nothing to install:
  ChaosHeadNoah_PSP_EN.patch.bin   the new sectors, back to back
  ChaosHeadNoah_PSP_EN.patch.txt   index:
      size <bytes>                  size of both ISOs
      source_sha256 <hex>           original Japanese ISO
      result_sha256 <hex>           patched English ISO
      copy <iso sector> <sector in the original ISO> <count>
      block <iso sector> <sector in .bin> <count>
  Patchers start from a copy of the original, then apply the lines (copies read the original file).
"""
import sys, os, hashlib

SECTOR = 2048
CHUNK = SECTOR * 8192
NAME = 'ChaosHeadNoah_PSP_EN.patch'


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
    ops = []            # [kind, dst start, src/bin start, count]
    sha_dst, nbin = hashlib.sha256(), 0
    with open(os.path.join(outdir, NAME + '.bin'), 'wb') as binf:
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
    lines = ['size %d' % size, 'source_sha256 %s' % sha_src.hexdigest(), 'result_sha256 %s' % sha_dst.hexdigest()]
    lines += ['%s %d %d %d' % tuple(o) for o in ops]
    with open(os.path.join(outdir, NAME + '.txt'), 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d copy runs, %d new-data runs, %.1f MB new data -> %s' % (
        sum(o[0] == 'copy' for o in ops), sum(o[0] == 'block' for o in ops), nbin * SECTOR / 1e6, outdir))


if __name__ == '__main__':
    main()
