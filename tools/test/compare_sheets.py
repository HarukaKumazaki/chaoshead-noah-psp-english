"""Side-by-side sheets (original | English) of every replaced picture, grouped by name prefix.
usage: compare_sheets.py  -> work/audit/cmp/<group>_<n>.png (8 pairs per sheet)"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import klz, tim2, p2t
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'work', 'audit', 'cmp'); os.makedirs(OUT, exist_ok=True)
W = 300


def load(path, k=None):
    if path.upper().endswith('.P2T'):
        b = open(path, 'rb').read()
        return p2t.image(b, p2t.entries(b)[k])[0].convert('RGBA')
    return tim2.read(klz.decompress(open(path, 'rb').read()))[0].convert('RGBA')


def flat(im):
    bg = Image.new('RGBA', im.size, (70, 70, 70, 255)); bg.alpha_composite(im)
    bg.thumbnail((W, W)); return bg


pairs = {}
for arch in ('DATA0', 'DATA1'):
    ovd = os.path.join(ROOT, 'work', 'ov', arch)
    if not os.path.isdir(ovd):
        continue
    for sub in sorted(os.listdir(ovd)):
        if sub.startswith(('SCENE', 'FONTS', 'CONFIG')) or sub.startswith('BGS'):
            continue
        for f in sorted(os.listdir(os.path.join(ovd, sub))):
            o, n = os.path.join(ROOT, 'unpacked', arch, sub, f), os.path.join(ovd, sub, f)
            if not os.path.exists(o):
                continue
            g = re.sub(r'[\d_]+.*$', '', f.split('.')[0]) or 'misc'
            if f.upper().endswith('.P2T'):
                b = open(n, 'rb').read(); bo = open(o, 'rb').read()
                for k in range(len(p2t.entries(b))):
                    if p2t.raw(b, p2t.entries(b)[k]) != p2t.raw(bo, p2t.entries(bo)[k]):
                        pairs.setdefault('P2T', []).append(('%s#%d' % (f, k), o, n, k))
            elif f.upper().endswith('.KLZ'):
                pairs.setdefault(g, []).append((f, o, n, None))
for g, items in pairs.items():
    for s in range(0, len(items), 8):
        chunk = items[s:s + 8]
        sheet = Image.new('RGBA', (2 * W + 30, len(chunk) * (W + 16)), (30, 30, 30, 255))
        d = ImageDraw.Draw(sheet)
        for r, (name, o, n, k) in enumerate(chunk):
            try:
                a, b = flat(load(o, k)), flat(load(n, k))
            except Exception:
                continue
            y = r * (W + 16)
            d.text((2, y), name, fill=(255, 255, 0, 255))
            sheet.paste(a, (0, y + 12)); sheet.paste(b, (W + 20, y + 12))
        sheet.save(os.path.join(OUT, '%s_%02d.png' % (g, s // 8)))
print({g: len(v) for g, v in pairs.items()})
