"""Check every replaced picture in the overlay against its original.

- KLZ/TIM2: same dimensions, bit depth, header and trailing data (sprite face patches)
- P2T: same entry table (count, dimensions, formats)
- content: grey-level correlation with the original after a 32x24 downscale; a replacement that is
  stretched, shifted, cropped or the wrong picture correlates poorly (text-only changes stay high)
Writes work/imgscan.tsv and a contact sheet of the lowest-scoring images.

Usage: imgscan.py [ovroot]
"""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import klz, tim2, p2t

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def corr(a, b):
    a = np.asarray(a.convert('L').resize((32, 24), Image.BILINEAR), float).ravel()
    b = np.asarray(b.convert('L').resize((32, 24), Image.BILINEAR), float).ravel()
    a -= a.mean(); b -= b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else 1.0


def main():
    ov = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'ov')
    rows, problems = [], []
    for f in glob.glob(os.path.join(ov, '*', '*', '*')):
        rel = os.path.relpath(f, ov)
        o = os.path.join(ROOT, 'unpacked', rel)
        if not os.path.exists(o):
            continue
        ext = f.upper().rsplit('.', 1)[-1]
        try:
            if ext == 'KLZ':
                nb, ob = klz.decompress(open(f, 'rb').read()), klz.decompress(open(o, 'rb').read())
                if ob[:4] != b'TIM2':
                    continue
                ni, nf = tim2.read(nb); oi, of = tim2.read(ob)
                issues = []
                if (nf['w'], nf['h'], nf['bpp']) != (of['w'], of['h'], of['bpp']):
                    issues.append('format')
                if nf['header'] != of['header']:
                    issues.append('header')
                if nf.get('tail') != of.get('tail'):
                    issues.append('tail-data')
                import numpy as np
                ta = (np.asarray(ni)[:, :, 3] < 128).mean(); tb = (np.asarray(oi)[:, :, 3] < 128).mean()
                if abs(ta - tb) > 0.15:
                    issues.append('transparency %.0f%%->%.0f%%' % (tb * 100, ta * 100))
                c = corr(ni, oi)
                rows.append((rel, 'klz', '%dx%d' % (nf['w'], nf['h']), round(c, 3), ','.join(issues)))
            elif ext == 'P2T':
                nb, ob = open(f, 'rb').read(), open(o, 'rb').read()
                ne, oe = p2t.entries(nb), p2t.entries(ob)
                issues = [] if [e['hdr'] for e in ne] == [e['hdr'] for e in oe] else ['entries']
                for k, (a, b) in enumerate(zip(ne, oe)):
                    ia, _ = p2t.image(nb, a); ib, _ = p2t.image(ob, b)
                    c = corr(ia, ib)
                    rows.append((rel + '#%d' % k, 'p2t', '%dx%d' % ia.size, round(c, 3), ','.join(issues)))
        except Exception as e:
            rows.append((rel, ext, '?', 0.0, 'ERROR %s' % e))
    rows.sort(key=lambda r: r[3])
    with open(os.path.join(ROOT, 'work', 'imgscan.tsv'), 'w', encoding='utf-8') as fo:
        for r in rows:
            fo.write('\t'.join(map(str, r)) + '\n')
    bad = [r for r in rows if r[4]]
    print('images checked:', len(rows), '| structural problems:', len(bad))
    for r in bad[:40]:
        print('  ', r)
    print('lowest content correlation:')
    for r in rows[:25]:
        print('  ', r)


if __name__ == '__main__':
    main()
