"""Re-typeset wrapped text-log images in English: the Committee terminal (CHAT_S_*) and the ESO
in-game logs (MMO_*), from CoZ's lines for the same scene.

Pages show a contiguous run of wrapped rows (18 px pitch, chronological, may start mid-message).
The Japanese messages are wrapped with the page's metrics to predict row widths, the page's
measured rows are located in that sequence, and the same span is re-wrapped in English.

Usage: logimg.py ovroot
"""
import sys, os, re, glob, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import klz, tim2, msb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LBF = r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier'
FONT = os.path.join(LBF, 'fonts', 'VL-PGothic-Regular.ttf')
FONT_X = os.path.join(LBF, 'subs', 'fonts', 'Doulos SIL.ttf')     # Cyrillic for the garbled sender

STYLES = {
    # name pattern, separator in JP / EN, x0, wrap width, pitch, first row y, ink test, text colour, bg
    'term': dict(sep_jp='：', sep_en=': ', x0=38, wrap=396, pitch=18, y0=2, dark=False, fg=(235, 235, 235, 255),
                 bg=(0, 0, 0, 0), size=14),
    'mmo': dict(sep_jp='＞', sep_en=' > ', x0=7, wrap=380, pitch=18, y0=9, dark=True, fg=(16, 16, 16, 255),
                bg=None, size=14),
}


METRICS = {'term': (15, 8), 'mmo': (14.5, 6.5)}   # fitted full-/half-width advance per style
_cur = ['term']


def cw(c):
    fw, hw = METRICS[_cur[0]]
    n = unicodedata.normalize('NFKC', c)[:1] or c
    return hw if unicodedata.east_asian_width(n) in 'NaH' else fw


def wrap_jp(t, width):
    rows, cur = [], 0
    for ch in t:
        if cur + cw(ch) > width:
            rows.append(cur); cur = 0
        cur += cw(ch)
    rows.append(cur)
    return rows


def measure(img, st):
    g = img.convert('L'); w, h = g.size; px = g.load()
    out = []
    y = st['y0']
    while y + 14 <= h:
        xs = [x for yy in range(y, y + 15) for x in range(w)
              if (px[x, yy] < 100 if st['dark'] else px[x, yy] > 120)]
        out.append((y, (max(xs) - st['x0']) if xs else 0))
        y += st['pitch']
    return out


def lines_for(prefix, sep):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'steam', 'mes00', prefix + '*_00.msb'))):
        n = os.path.basename(f)[:-7]
        en = dict(msb.mes(msb.en_file(n + '_01.msb')))
        for i, raw in msb.mes(f):
            t = msb.dec(raw, False)
            if sep in t[:14] or t.startswith('GUEST：'):
                out.append((t.replace('\n', ''), msb.dec(en.get(i, b'\xff'), False).replace('\n', ' ')))
    return out


def locate(meas, lines, st):
    pred = []                     # (message index, row index within message, width)
    for m, (jp, en) in enumerate(lines):
        for r, w in enumerate(wrap_jp(jp, st['wrap'])):
            pred.append((m, r, w))
    filled = [(k, w) for k, (y, w) in enumerate(meas) if w > 0]
    if not filled:
        return None, 999
    best = None
    for s in range(len(pred)):
        err, n = 0, 0
        for k, w in filled:
            if s + k >= len(pred):
                err += 300
            else:
                err += min(abs(pred[s + k][2] - w), 300)
            n += 1
        e = err / n
        if best is None or e < best[0]:
            best = (e, s)
    return pred[best[1]], best[0]


def wrap_en(text, font, width):
    rows, cur = [], ''
    for word in text.split(' '):
        t = (cur + ' ' + word) if cur else word
        if font.getlength(t) <= width:
            cur = t
        else:
            if cur:
                rows.append(cur)
            cur = word
    rows.append(cur)
    return rows


def render(orig, meas, lines, start, st):
    m0, r0, _ = start
    img = orig.convert('RGBA').copy()
    d = ImageDraw.Draw(img)
    bg = st['bg'] or img.getpixel((img.width - 2, 2))
    d.rectangle((0, 0, img.width, img.height), fill=bg)
    font = ImageFont.truetype(FONT, st['size'])
    fx = ImageFont.truetype(FONT_X, st['size'])
    rows = []
    for m in range(m0, len(lines)):
        jp, en = lines[m]
        r = wrap_en(en, font, st['wrap'])
        if m == m0 and r0:          # page starts mid-message: skip the same share of English rows
            jr = len(wrap_jp(jp, st['wrap']))
            r = r[min(len(r) - 1, round(r0 * len(r) / jr)):]
        rows += r
        if len(rows) >= len(meas):
            break
    for k, (y, w) in enumerate(meas):
        if k >= len(rows):
            break
        text = rows[k]
        x = st['x0']
        for ch in text:                 # per-character font fallback for the Cyrillic mojibake
            f = fx if ord(ch) > 0x2000 and ord(ch) < 0x3000 or 0x400 <= ord(ch) < 0x500 or ch in '¦€¶' else font
            d.text((x, y + 13), ch, font=f, fill=st['fg'], anchor='ls')
            x += f.getlength(ch)
    return img


def paginate(series, lines, st):
    """pages of one series in order: each holds the messages the Japanese page could fit"""
    m = 0
    out = []
    for f, orig, info in series:
        meas = measure(orig, st)
        cap = max([k + 1 for k, (y, w) in enumerate(meas) if w > 0] or [0])
        used, first = 0, m
        while m < len(lines):
            need = len(wrap_jp(lines[m][0], st['wrap']))
            if used + need > cap and m > first:
                break
            used += need; m += 1
        out.append((f, orig, info, meas[:cap], first, m))
    return out


def render_block(orig, meas, msgs, st):
    img = orig.convert('RGBA').copy()
    d = ImageDraw.Draw(img)
    bg = st['bg'] if st['bg'] is not None else img.getpixel((img.width - 2, 2))
    img = Image.new('RGBA', img.size, bg); d = ImageDraw.Draw(img)
    size = st['size']
    while True:
        font = ImageFont.truetype(FONT, size)
        rows = [r for jp, en in msgs for r in wrap_en(en, font, st['wrap'])]
        if len(rows) <= len(meas) or size <= 10:
            break
        size -= 1
    fx = ImageFont.truetype(FONT_X, size)
    pitch = st['pitch'] if len(rows) <= len(meas) else max(12, st['pitch'] * len(meas) // len(rows))
    y = meas[0][0] if meas else st['y0']
    for text in rows:
        x = st['x0']
        for ch in text:
            f = fx if (0x400 <= ord(ch) < 0x500 or ch in '¦€¶') else font
            d.text((x, y + 13), ch, font=f, fill=st['fg'], anchor='ls')
            x += f.getlength(ch)
        y += pitch
    return img


MMO_FG = (235, 235, 235, 255)
SLOTS = 28                      # rows per 512px page: y = 9 + 18*i
MMO_SIZE = 12


def jp_rows(img):
    """slot indices (0..27) that hold text on a Japanese MMO page"""
    import numpy as np
    a = np.asarray(img.convert('RGBA'))[:, :, 3]
    return [i for i in range(SLOTS) if a[9 + 18 * i:9 + 18 * i + 15].max() > 0]


def mmo_series(files, lines, d, ov):
    """pages A1..An stack bottom-up (An on top); the log is newest-first and ends at A1's last
    slot. English is laid out the same way, never using more rows than the Japanese did."""
    pages = [(f,) + tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read())) for f in files]
    pages.sort(key=lambda p: p[0])
    # consecutive pages overlap: the bottom slots of page n+1 repeat the top slots of page n
    import numpy as np
    def slot(img, i):
        return np.asarray(img.convert('RGBA'))[9 + 18 * i:9 + 18 * i + 16]
    base = [0]
    for (fa, ia, _), (fb, ib, _) in zip(pages, pages[1:]):
        ov_n = 0
        for k in range(1, SLOTS):
            if all(slot(ia, j).any() and np.abs(slot(ia, j).astype(int) - slot(ib, SLOTS - k + j)).mean() < 1 for j in range(k)):
                ov_n = k
        base.append(base[-1] + SLOTS - ov_n)
    # every ESO log uses the same size (mixed sizes looked like thinner messages); the English may
    # also fill the top page's empty slots, and only shrinks if even that is not enough
    used = base[-1] + SLOTS
    msgs = [en for jp, en in lines][::-1]                       # newest first
    for size in (MMO_SIZE, 11, 10):
        font = ImageFont.truetype(FONT, size)
        rows = [r for en in msgs for r in wrap_en(en, font, 400)]
        if len(rows) <= (used or 10 ** 9):
            break
    # global slot index counted from the bottom of A1 upwards
    out = []
    for pi, (f, img, info) in enumerate(pages):
        canvas = Image.new('RGBA', img.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(canvas)
        for i in range(SLOTS):
            g = base[pi] + (SLOTS - 1 - i)                        # position from the bottom
            k = len(rows) - 1 - g
            if 0 <= k < len(rows):
                dr.text((7, 9 + 18 * i + 13), rows[k], font=font, fill=MMO_FG, anchor='ls')
        out.append((f, canvas, info))
    return out, len(rows), base, size


def main():
    ov = sys.argv[1]
    d = os.path.join(ROOT, 'unpacked', 'DATA0', 'BGL00.AFS.d')
    series = {}
    for f in sorted(os.listdir(d)):
        m = re.fullmatch(r'CHAT_S_(\d\d\d)A\d\.KLZ', f)
        m2 = re.fullmatch(r'MMO_(\d\d)_(\d\d\d)A\d\.KLZ', f)
        if m:
            series.setdefault(('term', 'schs_' + m.group(1)), []).append(f)
        elif m2:
            series.setdefault(('mmo', 'sch%s_%s' % (m2.group(1), m2.group(2))), []).append(f)
    n = 0
    for (style, prefix), files in series.items():
        st = STYLES[style]; _cur[0] = style
        lines = lines_for(prefix, st['sep_jp'])
        if style == 'mmo':
            res, nr, used, size = mmo_series(files, lines, d, ov)
            od = os.path.join(ov, 'DATA0', 'BGL00.AFS.d'); os.makedirs(od, exist_ok=True)
            for f, img, info in res:
                open(os.path.join(od, f), 'wb').write(klz.compress(tim2.write(img, info))); n += 1
            print(prefix, 'ESO rows', nr, 'of', used, 'size', size)
            continue
        pages = []
        for f in files:
            orig, info = tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read()))
            pages.append((f, orig, info))
        for f, orig, info, meas, a, b in paginate(pages, lines, st):
            out = render_block(orig, meas, lines[a:b], st)
            od = os.path.join(ov, 'DATA0', 'BGL00.AFS.d'); os.makedirs(od, exist_ok=True)
            open(os.path.join(od, f), 'wb').write(klz.compress(tim2.write(out, info)))
            n += 1
            print(f, 'messages', a, '-', b, 'of', len(lines))
    print('log pages typeset:', n)


if __name__ == '__main__':
    main()
