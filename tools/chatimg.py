"""Re-typeset PSP chat-log pages (CHAT_*.KLZ) in English from CoZ's chat lines.

Each page is 17 rows x 30 px, newest line at the top, rows tinted by speaker. For every page the
rows are matched to a window of the scene's chat lines by text width (full-width 12 px,
half-width 6 px), then each row is redrawn as "Speaker: text" in the row's own colour.
Rows whose content is already ASCII (URLs) keep their original pixels after the new name.

Usage: chatimg.py ovroot
"""
import sys, os, re, glob, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import klz, tim2, msb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\fonts',
                    'VL-PGothic-Regular.ttf')
ROW, NROW = 30, 17
CHAT = re.compile(r'^([^：:\s「」]{1,10})[：:](.*)$')
NAMES = {'ナイトハルト': 'Neidhardt', 'グリム': 'Grimm', '将軍': 'Shogun', '蒋軍': 'Shougun'}
SYSMSG = re.compile('さんが(入室|退室)しました')


def jpw(t):
    return max(sum(6 if unicodedata.east_asian_width(c) in 'NaH' else 12 for c in ln) for ln in t.split('\n'))


def read_rows(img):
    """rows are the bands ending at each separator line (scroll offset varies per page);
    returns [(top_y, width, colour)] top to bottom; a half-visible top row is included"""
    g = img.convert('RGB'); w, h = g.size; px = g.load()
    seps = [y for y in range(h) if sum(1 for x in range(0, w, 4) if 60 < max(px[x, y]) < 200 and
                                         max(px[x, y]) - min(px[x, y]) < 30) > (w // 4) * 0.7]
    sep_rows = []
    for y in seps:                      # collapse 1-2 px thick lines
        if not sep_rows or y - sep_rows[-1] > 3:
            sep_rows.append(y)
    tops = [y - 26 for y in sep_rows]
    if sep_rows and h - sep_rows[-1] > 12:
        tops.append(sep_rows[-1] + 4)
    rows = []
    for top in tops:
        xs, cols = [], []
        for y in range(max(0, top + 3), min(h, top + 25)):
            for x in range(w):
                c = px[x, y]
                if max(c) > 110 and not (max(c) - min(c) < 30 and 60 < max(c) < 200):
                    xs.append(x); cols.append(c)
        if xs:
            n = len(cols)
            rows.append((top, max(xs), tuple(sum(c[i] for c in cols) // n for i in range(3))))
        else:
            rows.append((top, 0, None))
    return rows


def scene_lines(prefix):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'steam', 'mes00', prefix + '*_00.msb'))):
        n = os.path.basename(f)[:-7]
        en = dict(msb.mes(msb.en_file(n + '_01.msb')))
        for i, raw in msb.mes(f):
            t = msb.dec(raw, False)
            m = CHAT.match(t)
            if m or SYSMSG.search(t):
                out.append((t, msb.dec(en.get(i, b'\xff'), False)))
    return out


def speaker_of(col):
    r, g, b = col
    if r > 1.8 * g and r > 120:
        return 'red'
    if g > 1.4 * b and r > 1.2 * b:
        return 'yellow'
    return 'white'


SPEAKER_COLOUR = {'グリム': 'red', 'ナイトハルト': 'white', '将軍': 'yellow', '蒋軍': 'yellow'}


def line_colour(jp):
    m = CHAT.match(jp)
    return SPEAKER_COLOUR.get(m.group(1)) if m else None


def match(rows, lines):
    """local alignment of rows (top->bottom = newer->older) to lines; returns {row_index: line_index}
    and the mean width error of matched rows"""
    R = [k for k, (t, w, c) in enumerate(rows) if w]
    if not R:
        return {}, 0, 0
    L = list(range(len(lines) - 1, -1, -1))          # newest first
    W = [jpw(lines[j][0]) for j in L]
    C = [line_colour(lines[j][0]) for j in L]
    n, m = len(R), len(L)
    GAP = 10
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    B = [[0] * (m + 1) for _ in range(n + 1)]
    best = (0, 0, 0)
    for i in range(1, n + 1):
        t, w, col = rows[R[i - 1]]
        sp = speaker_of(col)
        for j in range(1, m + 1):
            sc = 24 - abs(W[j - 1] - w) / 4.0
            if C[j - 1] and C[j - 1] != sp:
                sc -= 40
            opts = (0.0, S[i - 1][j - 1] + sc, S[i - 1][j] - GAP, S[i][j - 1] - GAP)
            v = max(opts)
            S[i][j] = v; B[i][j] = opts.index(v)
            if v > best[0]:
                best = (v, i, j)
    i, j = best[1], best[2]
    pairs = {}
    while i > 0 and j > 0 and B[i][j]:
        if B[i][j] == 1:
            pairs[R[i - 1]] = L[j - 1]; i -= 1; j -= 1
        elif B[i][j] == 2:
            i -= 1
        else:
            j -= 1
    err = [abs(jpw(lines[l][0]) - rows[r][1]) for r, l in pairs.items()]
    return pairs, (sum(err) / len(err) if err else 999), len(R)


def render(orig, rows, lines, s):
    img = orig.convert('RGBA').copy()
    W, H = img.size
    for k, (top, w, col) in enumerate(rows):
        if w:   # averaged anti-aliased pixels are darker than the strokes: restore the peak brightness
            mx = max(col) or 1
            col = tuple(min(255, int(c * 235 / mx)) for c in col)
        if not w or k not in s:
            continue                                   # unmatched rows keep their original pixels
        jp, en = lines[s[k]]
        bg0 = (0, 0, 0, 0) if orig.convert('RGBA').getpixel((W - 2, top + 12 if top + 12 < H else H - 1))[3] == 0 else (0, 0, 0, 255)
        band = Image.new('RGBA', (W, 24), bg0)     # one row, drawn then pasted (may be cut off)
        d = ImageDraw.Draw(band)
        if SYSMSG.search(jp):                                   # two-line system notice
            f = ImageFont.truetype(FONT, 10)
            for n, ln in enumerate(en.split('\n')[:2]):
                d.text((4, 10 + n * 11), ln, font=f, fill=col + (255,), anchor='ls')
        else:
            name_jp, body_jp = CHAT.match(jp).groups()
            m = CHAT.match(en)
            name_en = m.group(1) if m else NAMES.get(name_jp, name_jp)
            body_en = m.group(2).strip() if m else en
            keep = None
            if body_jp.isascii():                                # URLs: reuse original pixels
                nx = jpw(name_jp + '：')
                keep = img.crop((nx, top + 2, W, top + 26))
            # URL rows keep the original '：' and address pixels after the English name
            text = ('%s: %s' % (name_en, body_en)) if keep is None else name_en
            size = 12
            f = ImageFont.truetype(FONT, size)
            while f.getlength(text) > W - 8 and size > 11:
                size -= 1; f = ImageFont.truetype(FONT, size)
            ink = dict(fill=col + (255,), anchor='ls', stroke_width=1, stroke_fill=(0, 0, 0, 255))
            if f.getlength(text) <= W - 8 or keep is not None:
                d.text((4, 17), text, font=f, **ink)
            else:                                              # too long: two lines in the row
                f = ImageFont.truetype(FONT, 10)
                words, l1 = text.split(' '), ''
                while words and f.getlength((l1 + ' ' + words[0]).strip()) <= W - 8:
                    l1 = (l1 + ' ' + words.pop(0)).strip()
                d.text((4, 10), l1, font=f, **ink)
                d.text((4, 21), ' '.join(words), font=f, **ink)
            if keep is not None:
                band.paste(keep, (int(f.getlength(text)) + 4, 0))
        if SYSMSG.search(jp):                  # the two-line notice starts above the row: clear it all
            px = img.load()
            for y in range(max(0, top - 14), top + 2):      # erase the ink, keep grey separator lines
                grey = sum(1 for x in range(0, W, 4) if 60 < max(px[x, y][:3]) < 200 and
                           max(px[x, y][:3]) - min(px[x, y][:3]) < 30)
                if grey < (W // 4) * 0.7:
                    for x in range(W):
                        px[x, y] = (0, 0, 0, 255)
        # clear the old row's ink (keep grey separator lines), then lay the new row over it
        px = img.load()
        for y in range(max(0, top + 2), min(H, top + 26)):
            grey = sum(1 for x in range(0, W, 4) if 60 < max(px[x, y][:3]) < 200 and
                       max(px[x, y][:3]) - min(px[x, y][:3]) < 30 and px[x, y][3])
            if grey < (W // 4) * 0.7:
                for x in range(W):
                    px[x, y] = bg0
        img.alpha_composite(band, (0, max(0, top + 2))) if top + 2 >= 0 else img.paste(band, (0, top + 2), band)
    return img


ALL_LINES = []

# rows the width matcher cannot place (older lines / system notices): pinned to their exact line
LEFT, JOIN = '蒋軍さんが退室しました\n現在のメンバー：1人', '蒋軍さんが入室しました\n現在のメンバー：2人'
PIN = {
    ('CHAT_01_003H2', 13): 'ナイトハルト：ま、スク水さえ着てれば他に余計なものはいらないってこった',
    ('CHAT_01_003H2', 14): 'ナイトハルト：スク水には甘酸っぱい青春の思い出という補正がかかっているのだ',
    ('CHAT_01_003H2', 15): 'ナイトハルト：メガネ？　そんなんいらね',
    ('CHAT_01_003H2', 16): 'ナイトハルト：そういう話なら、ちょっとした持論を披露してしんぜよう',
    ('CHAT_01_003B2', 8): 'ナイトハルト：でもあえて取らない！',
    ('CHAT_01_003G2', 14): 'ナイトハルト：スク水には甘酸っぱい青春の思い出という補正がかかっているのだ',
    ('CHAT_01_003G2', 16): 'ナイトハルト：胸の名札なんて飾りです。偉い人にはそれが分からんのです',
    ('CHAT_08_158A1', 0): '将軍：fun＾10×int＾40＝Ir2',
    ('CHAT_06_113A1', 0): LEFT, ('CHAT_06_113A1', 5): JOIN,
    ('CHAT_06_113B1', 0): LEFT, ('CHAT_06_113B1', 8): JOIN,
}


def chat_frame(orig):
    """chat window frame: relabel リロード / 入室 / 参加人数(1)"""
    img = orig.convert('RGBA').copy()
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 13)
    bg = img.getpixel((70, 30))
    d.rectangle((60, 6, 92, 34), fill=bg)                       # リロード label
    d.text((91, 26), 'Reload', font=ImageFont.truetype(FONT, 11), fill=(235, 235, 235, 255), anchor='rs')
    btn = img.getpixel((60, 30 + 26))
    d.rectangle((58, 28, 88, 44), fill=btn)                     # 入室 button face
    d.text((73, 41), 'Enter', font=ImageFont.truetype(FONT, 11), fill=(255, 255, 255, 255), anchor='ms')
    d.rectangle((92, 26, 160, 46), fill=img.getpixel((150, 50)))
    d.text((95, 41), 'Users (1)', font=f, fill=(235, 235, 235, 255), anchor='ls')
    return img


def main():
    ov = sys.argv[1]
    report = []
    for arch, sub in (('DATA0', 'BGL00.AFS.d'), ('DATA1', 'BGL01.AFS.d')):
        d = os.path.join(ROOT, 'unpacked', arch, sub)
        for f in sorted(os.listdir(d)):
            m = re.fullmatch(r'CHAT_(\d\d)_(\d\d\d)[A-Z]\d+\.KLZ', f)
            m2 = re.fullmatch(r'CHAT_([A-Z])_(\d\d\d)[A-Z]\d+\.KLZ', f)
            if m:
                lines = scene_lines('sch%s_%s' % (m.group(1), m.group(2)))
            elif m2:
                lines = scene_lines('sch%s_%s' % (m2.group(1).lower(), m2.group(2)))
            elif re.fullmatch(r'CHAT_[ABC]\d\.KLZ', f):
                orig, info = tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read()))
                od = os.path.join(ov, arch, sub); os.makedirs(od, exist_ok=True)
                open(os.path.join(od, f), 'wb').write(klz.compress(tim2.write(chat_frame(orig), info)))
                report.append((f, 'ok frame')); continue
            else:
                continue
            prefix = f
            orig, info = tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read()))
            rows = read_rows(orig)
            if not lines:
                report.append((f, 'no CoZ chat lines for ' + prefix)); continue
            pairs, err, nrows = match(rows, lines)
            for (pf, k), jp in PIN.items():
                if pf + '.KLZ' == f:
                    hit = [i for i, (j, e) in enumerate(lines) if j.replace('　', ' ') == jp.replace('　', ' ')]
                    if hit:
                        pairs[k] = hit[-1]
            if not pairs or err > 30:
                report.append((f, 'weak match %d/%d rows, err %.1f' % (len(pairs), nrows, err))); continue
            if len(pairs) < nrows:
                left = [k for k, (t, w, c) in enumerate(rows) if w and k not in pairs]
                report.append((f, 'partial: rows %s still Japanese' % left))
            s = pairs
            out = render(orig, rows, lines, s)
            od = os.path.join(ov, arch, sub)
            os.makedirs(od, exist_ok=True)
            open(os.path.join(od, f), 'wb').write(klz.compress(tim2.write(out, info)))
            report.append((f, 'ok %d/%d rows err %.1f' % (len(pairs), nrows, err)))
    ok = [r for r in report if r[1].startswith('ok')]
    print('chat pages typeset:', len(ok), 'of', len(report))
    for r in report:
        if not r[1].startswith('ok'):
            print('  ', r)


if __name__ == '__main__':
    main()
