"""Translate the menu/UI textures inside the OBJ_*.P2T containers (OBJSY.AFS).

- OBJ_LG #3: boot CAUTION screen -> CoZ's z_warning
- 480x18 button-guide bars: icons kept (located by shape), labels re-typeset in English
- help screens, voice-actor list, ending-song thumbnails, staff name

Usage: uitex.py ovroot
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import p2t

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'unpacked', 'DATA0', 'OBJSY.AFS.d')
LBF = r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier'
FONT = os.path.join(LBF, 'fonts', 'VL-PGothic-Regular.ttf')
SERIF = os.path.join(LBF, 'subs', 'fonts', 'IPAexMincho.ttf')

# ---------------------------------------------------------------- button bars
# per bar: sequence of (icon kind, label[, icon x]); a label starting with '-' is drawn disabled (grey).
# The icon x is given where template matching fails (an icon packed tight against its Japanese label).
B, P, L, R, D = 'btn', 'pill', 'L', 'R', 'dpad'
BARS = {
    'AB': {
        6: [(B, 'Mark'), (P, 'Mark All'), (L, 'Prev Page'), (R, 'Next Page')],
        7: [(B, 'Next'), (B, 'Back'), (B, 'Resize'), (B, 'Rotate'), (P, 'Hide Menu'), (L, ''), (R, 'Page'),
            (P, 'Screenshot')],
        8: [(B, 'Next'), (B, 'Back'), (B, '-Resize'), (B, 'Rotate'), (P, 'Hide Menu'), (L, ''), (R, 'Page'),
            (P, 'Screenshot')],
        9: [(B, 'Next'), (B, 'Back'), (B, 'Resize'), (B, 'Rotate'), (P, 'Hide Menu'), (L, ''), (R, 'Page'),
            (P, '-Screenshot')],
        10: [(B, 'Next'), (B, 'Back'), (B, '-Resize'), (B, 'Rotate'), (P, 'Hide Menu'), (L, ''), (R, 'Page'),
             (P, '-Screenshot')],
    },
    'CL': {
        4: [(L, 'Prev Page'), (R, 'Next Page')],
        5: [(L, 'Prev Page'), (R, 'Next Page'), (B, 'Play')],
    },
    'CM': {
        4: [(B, 'Mark'), (P, 'Mark All'), (L, 'Prev Page'), (R, 'Next Page')],
    },
    'MV': {
        4: [(B, 'Mark'), (P, 'Mark All'), (L, 'Prev Page'), (R, 'Next Page')],
    },
    'MU': {
        10: [(B, 'Play'), (B, 'Stop'), (D, 'Prev Track'), (D, 'Next Track'), (P, 'Hide Window')],
        6: [(B, 'Play'), (B, 'Back'), (B, 'Mode'), (B, 'Edit'), (P, 'Sort'), (P, 'Reset')],
        7: [(B, 'Delete'), (B, 'Back'), (B, 'Mode'), (D, 'Select'), (P, 'Sort'), (P, 'Reset')],
        8: [(B, 'Insert'), (B, 'Back'), (B, 'Mode'), (D, 'Select'), (P, 'Sort'), (P, 'Reset')],
        9: [(B, 'Back'), (B, 'Back'), (D, 'Select'), (D, 'Change')],
    },
    'SC': {
        26: [(L, 'Save/Load'), (P, 'View'), (P, 'Sort'), (R, 'Hide Window')],
        27: [(B, 'Lock'), (P, 'View'), (P, 'Sort'), (R, 'Hide Window')],
        28: [(P, 'View', 5), (P, 'Sort'), (R, 'Hide Window')],
        29: [(P, 'Sort')],
        30: [(B, 'Confirm'), (P, 'View'), (P, 'Sort')],
        31: [(B, 'Back')],
        32: [(B, 'Back'), (L, 'Prev Page'), (R, 'Next Page')],
        33: [(B, 'Confirm'), (B, 'Back'), (D, 'Move Cursor'), (D, 'Change Item')],
        34: [(B, '-Confirm'), (B, 'Back'), (D, 'Move Cursor'), (D, 'Change Item')],
        35: [(B, 'Cursor Mode'), (B, 'Back'), (L, 'Top'), (R, 'Bottom')],
        36: [(B, 'Load'), (B, 'Play All'), (B, 'Play Voice'), (L, 'Top'), (R, 'Bottom'), (B, 'Back')],
        37: [(B, 'Stop'), (B, 'Stop')],
        38: [(B, 'Next'), (B, 'Stop')],
    },
}

_bg = None
_tpl = {}


def _mask(a):
    return np.abs(a[:, :, :3].astype(int) - _bg[:, :, :3].astype(int)).sum(2) > 25


def clean_bar_bg(images):
    """the bar background (identical in every bar) from columns that show the plain scanline pattern"""
    from collections import Counter
    A = np.stack([np.asarray(im.convert('RGBA')) for im in images]).astype(int)
    out = np.zeros((18, 480, 4), np.uint8); out[:, :, 3] = 255
    miss = []
    for x in range(480):
        c = Counter(tuple(A[i, :, x, :3].flatten()) for i in range(len(A)))
        for col, n in c.most_common():
            arr = np.array(col).reshape(18, 3)
            if x >= 300 or ((arr[2:17:2] == arr[2]).all() and (arr[3:16:2] == arr[3]).all()):
                out[:, x, :3] = arr
                break
        else:
            miss.append(x)
    good = [x for x in range(480) if x not in miss]
    for x in miss:
        l = max([g for g in good if g < x], default=None); r = min(g for g in good if g > x)
        out[:, x, :3] = out[:, r, :3] if l is None else (out[:, l, :3] * (r - x) + out[:, r, :3] * (x - l)) // (r - l)
    return out


THRESH = dict(btn=0.7, pill=0.85, L=0.85, R=0.85, dpad=0.85)


def locate(m, kind, start):
    """first good match (IoU >= 0.75, local maximum) of an icon template of `kind` at x >= start"""
    sc = []
    for t in _tpl[kind]:
        w = t.shape[1]
        for x in range(start, 480 - w + 1):
            win = m[:, x:x + w]
            uni = (win | t).sum()
            sc.append(((win & t).sum() / uni if uni else 0, x, w))
    by_x = {}
    for s, x, w in sc:
        if s > by_x.get(x, (-1,))[0]:
            by_x[x] = (s, w)
    for x in sorted(by_x):
        s, w = by_x[x]
        if s >= THRESH[kind] and all(by_x.get(x + k, (0,))[0] <= s for k in range(-3, 4)):
            return x, w
    s, x, w = max(sc)
    return x, w


def bar_font(size):
    return ImageFont.truetype(FONT, size)


def draw_label(img, x, text, size, grey):
    d = ImageDraw.Draw(img)
    f = bar_font(size)
    fill = (120, 120, 120, 255) if grey else (255, 255, 255, 255)
    d.text((x, 13), text, font=f, fill=fill, anchor='ls', stroke_width=1, stroke_fill=(0, 0, 0, 255))
    return f.getlength(text)


def render_bar(orig, seq):
    a = np.asarray(orig.convert('RGBA'))
    m = _mask(a)
    pos, x = [], 0
    for item in seq:
        kind = item[0]
        ix, w = (item[2], _tpl[kind][0].shape[1]) if len(item) > 2 else locate(m, kind, x)
        pos.append((ix, w))
        x = ix + w
    seq = [item[:2] for item in seq]
    for size in (12, 11, 10):
        f = bar_font(size)
        total = pos[0][0] + sum(w + 3 + (f.getlength(lb.lstrip('-')) + 7 if lb else 1) for (ix, w), (k, lb) in zip(pos, seq))
        if total <= 478:
            break
    out = Image.fromarray(_bg.copy())
    x = pos[0][0]
    for (ix, w), (kind, label) in zip(pos, seq):
        icon = Image.fromarray(a[:, ix:ix + w])
        icon_mask = Image.fromarray((m[:, ix:ix + w] * 255).astype(np.uint8))
        out.paste(icon, (x, 0), icon_mask)
        x += w + 3
        if label:
            grey = label.startswith('-')
            x += int(round(draw_label(out, x, label.lstrip('-'), size, grey))) + 7
        else:
            x += 1
    # keep the top highlight line of the original bar
    out.paste(Image.fromarray(a[0:1]), (0, 0))
    return out


def bars(files):
    global _bg
    ims = {}
    for pref, d in BARS.items():
        b = files[pref]
        es = p2t.entries(b)
        for i in d:
            ims[(pref, i)] = p2t.image(b, es[i])
    allbars = []
    for pref in ('AB', 'CL', 'CM', 'MU', 'MV', 'SC'):
        b = files[pref]
        for e in p2t.entries(b):
            img, info = p2t.image(b, e)
            if (info['w'], info['h']) == (480, 18):
                allbars.append(img)
    _bg = clean_bar_bg(allbars)
    m7 = _mask(np.asarray(ims[('AB', 7)][0].convert('RGBA')))
    c4 = _mask(np.asarray(ims[('CL', 4)][0].convert('RGBA')))
    s33 = _mask(np.asarray(ims[('SC', 33)][0].convert('RGBA')))
    _tpl.update(btn=[m7[:, 1:18]], pill=[m7[:, 173:198]], L=[m7[:, 261:281], c4[:, 7:27]],
                R=[m7[:, 281:302], c4[:, 78:98]], dpad=[s33[:, 85:102]])
    out = {}
    for (pref, i), (img, info) in ims.items():
        out.setdefault(pref, {})[i] = (render_bar(img, BARS[pref][i]), info)
    return out


# ---------------------------------------------------------------- CAUTION
def caution():
    im = Image.open(os.path.join(ROOT, 'steam', 'c0data', 'z_warning.webp')).convert('RGBA')
    im = im.resize((480, 270), Image.LANCZOS)
    out = Image.new('RGBA', (480, 272), (0, 0, 0, 255))
    out.paste(im, (0, 1))
    # the source picture has a mouse pointer over the last underline: keep only the red ink there
    px = out.load()
    for y in range(132, 162):
        for x in range(344, 372):
            r, g, b, a = px[x, y]
            if not (r > 90 and r > 2 * max(g, b)):
                px[x, y] = (0, 0, 0, 255)
    return out


# ---------------------------------------------------------------- misc pictures
def fit(text, font_path, width, size, minsize=7):
    while size > minsize:
        f = ImageFont.truetype(font_path, size)
        if f.getlength(text) <= width:
            return f
        size -= 1
    return ImageFont.truetype(font_path, minsize)


def voice_list(img):
    """OBJ_CM #2: three cards '陵 いのり役（小林 沙苗）' -> 'Inori Misasagi / CV: Sanae Kobayashi'"""
    img = img.copy()
    d = ImageDraw.Draw(img)
    rows = [('Inori Misasagi', 'CV: Sanae Kobayashi'), ('Miyabi Fujiwara', 'CV: Yumi Kakazu'),
            ('Karin Hanamatsuri', 'CV: Atsuko Enomoto')]
    h = img.height // 3
    for k, (a, b) in enumerate(rows):
        y0 = k * h
        bgc = img.getpixel((img.width - 12, y0 + h // 2))
        d.rectangle((92, y0 + 4, img.width - 6, y0 + h - 5), fill=bgc)
        f = fit(a, SERIF, img.width - 104, 16)
        d.text((img.width - 10, y0 + 22), a, font=f, fill=(20, 20, 20, 255), anchor='rs')
        f = fit(b, SERIF, img.width - 104, 13)
        d.text((img.width - 10, y0 + 42), b, font=f, fill=(20, 20, 20, 255), anchor='rs')
    return img


SONGS = {(2, 0): 'Motomeru Saki no Fuuga', (0, 1): 'Birthday☆Splash', (1, 1): 'Boku no Wish'}


def song_thumbs(img):
    """OBJ_MV #2 (360x168, 3x2 cards): retitle the Japanese song names in the cards' bottom strip"""
    img = img.copy()
    d = ImageDraw.Draw(img)
    cw, ch = 120, 84
    for (cx, cy), title in SONGS.items():
        x0, y0 = cx * cw, cy * ch
        strip = (x0 + 3, y0 + ch - 20, x0 + cw - 4, y0 + ch - 5)
        # sample the card colours just above the strip for a soft backing
        bgc = img.getpixel((x0 + 8, y0 + ch - 22))
        d.rectangle(strip, fill=bgc)
        f = fit(title, SERIF, cw - 12, 11)
        d.text((x0 + cw - 7, y0 + ch - 8), title, font=f, fill=(30, 40, 120, 255), anchor='rs',
               stroke_width=1, stroke_fill=(255, 255, 255, 255))
    return img


def staff_name(img):
    """OBJ_SC #58: '柏木　きら' (320x20 white text)"""
    out = Image.new('RGBA', img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(out)
    d.text((1, 16), 'Kira Kashiwagi', font=ImageFont.truetype(FONT, 17), fill=(255, 255, 255, 255), anchor='ls')
    return out


# ---------------------------------------------------------------- help screens
# controls help (OBJ_HE #2 = OBJ_SC #39): box rectangle -> lines; a tuple is (bold title, text) on one row
HELP = [
    ((46, 34, 186, 67), [('L Button', 'Show TIPS'), ('', 'Switch screen')]),
    ((239, 34, 406, 67), [('R Button', 'Force skip (hold)'), ('', 'Switch screen')]),
    ((269, 79, 399, 97), ['Open the backlog']),
    ((269, 98, 415, 143), ['Confirm menu / choice', 'Advance message', 'Start Auto Mode (hold)']),
    ((269, 145, 476, 189), ['Hide message window', 'Cancel menu / Close', 'Stop Auto Mode / Message Skip']),
    ((269, 191, 419, 209), ['Open the System Menu']),
    ((5, 213, 150, 269), [('D-Pad', 'Move cursor'), ('D-Pad ↑↓', 'Advance text'),
                          ('D-Pad ←→', 'Turn page')]),
    ((163, 213, 252, 269), [('Analog Pad', ''), ' Left: Positive', ' Right: Negative']),
    ((269, 218, 471, 236), [('START Button', 'Start Message Skip')]),
    ((269, 239, 471, 257), [('SELECT Button', 'Start Auto Mode')]),
]
INK = (34, 34, 46, 255)


def help_screen(img):
    img = img.copy()
    d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1), lines in HELP:
        d.rectangle((x0 + 3, y0 + 3, x1 - 3, y1 - 3), fill=(0xcd, 0xe7, 0xf5, 255))
        n = len(lines)
        pitch = (y1 - y0 - 4) / n
        titles = [ln[0] for ln in lines if isinstance(ln, tuple) and ln[0]]
        tf = ImageFont.truetype(FONT, 12)
        tw = max([tf.getlength(t) for t in titles], default=0)
        for k, ln in enumerate(lines):
            base = y0 + 2 + pitch * (k + 0.5) + 4.5
            if isinstance(ln, tuple):
                t, body = ln
                if t:
                    for dx in (0, 0.6):
                        d.text((x0 + 6 + dx, base), t, font=tf, fill=INK, anchor='ls')
                bx = x0 + 6 + (tw + 8 if tw else 0)
                if t and not body:
                    continue
                f = fit(body, FONT, x1 - 4 - bx, 11)
                d.text((bx, base), body, font=f, fill=INK, anchor='ls')
            else:
                f = fit(ln, FONT, x1 - x0 - 10, 12)
                d.text((x0 + 6, base), ln, font=f, fill=INK, anchor='ls')
    return img


def main():
    ov = os.path.join(sys.argv[1], 'DATA0', 'OBJSY.AFS.d')
    os.makedirs(ov, exist_ok=True)
    files = {n: open(os.path.join(SRC, 'OBJ_%s.P2T' % n), 'rb').read()
             for n in ('AB', 'CL', 'CM', 'HE', 'LG', 'MA', 'MU', 'MV', 'PR', 'SC', 'TT', 'WI')}
    new = {}

    def put(pref, i, img, info):
        new.setdefault(pref, {})[i] = p2t.tim2_raw(img, info)

    b = files['LG']; e = p2t.entries(b)[3]
    put('LG', 3, caution(), p2t.image(b, e)[1])
    for pref, d in bars(files).items():
        for i, (img, info) in d.items():
            put(pref, i, img, info)
    for pref, i, fn in (('CM', 2, voice_list), ('MV', 2, song_thumbs), ('SC', 58, staff_name),
                        ('HE', 2, help_screen), ('SC', 39, help_screen)):
        img, info = p2t.image(files[pref], p2t.entries(files[pref])[i])
        put(pref, i, fn(img), info)
    for pref, d in new.items():
        open(os.path.join(ov, 'OBJ_%s.P2T' % pref), 'wb').write(p2t.rebuild(files[pref], d))
    print('UI textures translated:', sum(len(d) for d in new.values()), 'in', len(new), 'P2T files')


if __name__ == '__main__':
    main()
