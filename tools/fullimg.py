"""Full-screen text cards (BGL00 FULL_CH*) re-typeset in English.

- FULL_CH08_170_001, FULL_CH09_189_*: white text centred on black (ch.8 / ch.9 delusion scenes)
- FULL_CH10_207_*: bold black text with white rim on white, left aligned, wrapped (ch.10 battle)
Each card shows one script line; the English is taken from the injected script report
(sch10_207: the %FS lines in order; sch09_189: Mia's parallel lines + the closing narration).

Usage: fullimg.py ovroot [report.tsv]
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import klz, tim2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BGL = os.path.join(ROOT, 'unpacked', 'DATA0', 'BGL00.AFS.d')
FONT = os.path.join(r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\fonts',
                    'VL-PGothic-Regular.ttf')


def clean(t):
    t = re.sub(r'【[^】]*】', '', t)
    t = re.sub(r'%(?:FS|FE|K|P|N|S\d{3}|T\d{3}|B\d[SE])', lambda m: ' ' if m.group(0) == '%N' else '', t)
    return re.sub(r'\s+', ' ', t).strip()


def wrap(text, font, width):
    rows, cur = [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w) if cur else w
        if font.getlength(t) <= width or not cur:
            cur = t
        else:
            rows.append(cur); cur = w
    rows.append(cur)
    return rows


def card(path, text, style):
    img, info = tim2.read(klz.decompress(open(path, 'rb').read()))
    a = np.asarray(img.convert('RGB')).astype(int)
    bgc = tuple(a[2, 2])
    diff = np.abs(a - np.array(bgc)).sum(2) > 60
    ys, xs = np.nonzero(diff)
    alpha0 = np.asarray(img.convert('RGBA'))[2, 2, 3]
    out = Image.new('RGBA', img.size, bgc + (255,) if alpha0 else bgc + (0,))   # keep the original's invisible colour (filter edges)
    if not alpha0:                              # transparent overlay: measure ink by alpha
        al = np.asarray(img.convert('RGBA'))[:, :, 3]
        ys, xs = np.nonzero(al > 0)
    d = ImageDraw.Draw(out)
    if style == 'dark':
        f = ImageFont.truetype(FONT, 14)
        rows = wrap(text, f, 440)
        cy = (ys.min() + ys.max()) / 2 if len(ys) else 136
        y0 = cy - (len(rows) - 1) * 9
        for k, r in enumerate(rows):
            d.text((240, y0 + k * 18), r, font=f, fill=(255, 255, 255, 255), anchor='mm')
    else:
        f = ImageFont.truetype(FONT, 16)
        rows = wrap(text, f, 450)
        x0 = xs.min() if len(xs) else 15
        top = ys.min() if len(ys) else 130
        for k, r in enumerate(rows):
            d.text((x0, top + 14 + k * 22), r, font=f, fill=(240, 240, 240, 255), anchor='ls',
                   stroke_width=1, stroke_fill=(0, 0, 0, 255))
    return klz.compress(tim2.write(out, info))


def main():
    ov = os.path.join(sys.argv[1], 'DATA0', 'BGL00.AFS.d'); os.makedirs(ov, exist_ok=True)
    rep = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'work', 'report.tsv')
    rows = [ln.rstrip('\n').split('\t') for ln in open(rep, encoding='utf-8')]
    fs207 = sorted(((int(r[1]), r[4]) for r in rows if r[0] == 'sch10_207' and r[1] != '-1' and '%FS' in r[3]))
    mia = [r[4] for r in rows if r[0] == 'sch09_189' and r[1] == '-1' and
           (r[3].startswith('【美愛】') or r[3].startswith(('あまりにも', 'そして、涙')))]
    hatano = [r[4] for r in rows if r[0] == 'sch08_170' and '【波多野３】' in r[3] and '望んだ妄想' in r[3]]
    jobs = [('FULL_CH08_170_001', hatano[0], 'dark')]
    jobs += [('FULL_CH09_189_%03d' % (k + 1), t, 'dark') for k, t in enumerate(mia[:12])]
    jobs += [('FULL_CH10_207_%03d' % (k + 1), t, 'light') for k, (ln, t) in enumerate(fs207)]
    n = 0
    for name, text, style in jobs:
        p = os.path.join(BGL, name + '.KLZ')
        if os.path.exists(p):
            open(os.path.join(ov, name + '.KLZ'), 'wb').write(card(p, clean(text), style)); n += 1
    print('full-screen cards:', n, '| ch10 lines', len(fs207), '| ch9 lines', len(mia))


if __name__ == '__main__':
    main()
