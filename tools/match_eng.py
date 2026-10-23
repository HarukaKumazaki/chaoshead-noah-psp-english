"""Match Steam's ID-named official English images (steam/bg_eng, steam/system_eng) to PSP KLZ images."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageChops, ImageStat
import klz, tim2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = (32, 24)


def thumb(im):
    return im.convert('L').resize(S, Image.BOX)


psp = {}
for arch, sub in (('DATA0', 'BGL00.AFS.d'), ('DATA1', 'BGL01.AFS.d')):
    d = os.path.join(ROOT, 'unpacked', arch, sub)
    for f in os.listdir(d):
        if f.endswith('.KLZ'):
            im, info = tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read()))
            psp[f[:-4]] = thumb(im)
res = {}
for src in ('bg_eng', 'system_eng'):
    d = os.path.join(ROOT, 'steam', src)
    for f in sorted(os.listdir(d)):
        try:
            im = Image.open(os.path.join(d, f))
        except Exception:
            continue
        w, h = im.size
        if abs(w / h - 4 / 3) > 0.02:
            res[src + '/' + f] = ('non-4:3 %dx%d' % (w, h), None); continue
        t = thumb(im)
        best = min((ImageStat.Stat(ImageChops.difference(t, p)).mean[0], n) for n, p in psp.items())
        res[src + '/' + f] = (best[1], round(best[0], 1), '%dx%d' % (w, h))
json.dump(res, open(os.path.join(ROOT, 'work', 'eng_match.json'), 'w'), indent=0)
for k, v in res.items():
    print(k, v)
