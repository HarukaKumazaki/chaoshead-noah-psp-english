"""Typeset the remaining one-off text images in English from CoZ's lines.

- BG_KARTE1/1A/1B: the medical-record questionnaire (questions = sch02_033 messages, in order)
- MMO_D02_043A-H: single ESO chat lines (sch02_043 '＞' lines, in order)
Usage: miscimg.py ovroot
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import klz, tim2, msb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\fonts',
                    'VL-PGothic-Regular.ttf')
BGL = os.path.join(ROOT, 'unpacked', 'DATA0', 'BGL00.AFS.d')


def en_lines(scene, pred):
    jp = msb.mes(os.path.join(ROOT, 'steam', 'mes00', scene + '_00.msb'))
    en = dict(msb.mes(msb.en_file(scene + '_01.msb')))
    return [msb.dec(en[i], False) for i, r in jp if pred(msb.dec(r, False))]


def text_rows(img, x0, x1, dark=True, thr=110):
    """y-bands containing dark (or light) ink between x0..x1"""
    g = img.convert('L'); px = g.load()
    ys = [y for y in range(img.height) if any((px[x, y] < thr) if dark else (px[x, y] > thr) for x in range(x0, x1))]
    bands = []
    for y in ys:
        if bands and y - bands[-1][1] <= 2:
            bands[-1][1] = y
        else:
            bands.append([y, y])
    return [(a, b) for a, b in bands if b - a >= 8]


def fit_font(text, width, size):
    while True:
        f = ImageFont.truetype(FONT, size)
        if f.getlength(text) <= width or size <= 8:
            return f
        size -= 1


def karte(path, questions):
    orig, info = tim2.read(klz.decompress(open(path, 'rb').read()))
    img = orig.convert('RGBA').copy()
    d = ImageDraw.Draw(img)
    rows = [r for r in text_rows(img, 40, 300) if r[0] > 80]      # question rows below the header
    for k, (a, b) in enumerate(rows):
        if k >= len(questions):
            break
        ink = img.getpixel((60, (a + b) // 2))
        bgc = img.getpixel((img.width - 6, (a + b) // 2))
        col = min((img.getpixel((x, y)) for x in range(40, 300) for y in range(a, b + 1)), key=lambda c: sum(c[:3]))
        d.rectangle((38, a - 1, img.width - 4, b + 1), fill=bgc)
        f = fit_font(questions[k], img.width - 44, 13)
        d.text((40, b), questions[k], font=f, fill=col, anchor='ls')
    return klz.compress(tim2.write(img, info))


def mmo_stack(path, texts):
    """MMO_D02_043A-H: the newest ESO lines, newest on top, rows from y=233 (18 px pitch)"""
    orig, info = tim2.read(klz.decompress(open(path, 'rb').read()))
    img = Image.new('RGBA', orig.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r, t in enumerate(texts):
        f = fit_font(t, img.width - 14, 14)
        d.text((7, 233 + 18 * r + 13), t, font=f, fill=(235, 235, 235, 255), anchor='ls')
    return klz.compress(tim2.write(img, info))


def main():
    ov = os.path.join(sys.argv[1], 'DATA0', 'BGL00.AFS.d')
    os.makedirs(ov, exist_ok=True)
    qs = en_lines('sch02_033', lambda t: True)
    n = 0
    for f in ('BG_KARTE1.KLZ', 'BG_KARTE1A.KLZ', 'BG_KARTE1B.KLZ'):
        open(os.path.join(ov, f), 'wb').write(karte(os.path.join(BGL, f), qs)); n += 1
    eso = en_lines('sch02_043', lambda t: '＞' in t[:10])
    for k, f in enumerate(sorted(x for x in os.listdir(BGL) if re.fullmatch(r'MMO_D02_043[A-H]\.KLZ', x))):
        if k < len(eso):
            texts = [eso[j] for j in range(k, max(-1, k - 3), -1)]
            open(os.path.join(ov, f), 'wb').write(mmo_stack(os.path.join(BGL, f), texts)); n += 1
    n += ensu_all(ov)
    print('misc images typeset:', n, '| ESO lines', len(eso), '| questions', len(qs))



# ESO character panel: CoZ renamed the player "knight-hart" -> "neidhardt" (ibg_ensu_win)
ENSU_NAME = {
    # name: (quad TL, TR, BR, BL) of the old name on the PSP picture
    'ENSU_WIN': ((359, 161), (391, 161), (391, 167), (359, 167)),
    'ENSU_DELUS_BG1A': ((359, 161), (391, 161), (391, 167), (359, 167)),
    'ENSU_DELUS_BG1B': ((359, 161), (391, 161), (391, 167), (359, 167)),
    'ENSU_DELUS_BG1C': ((359, 161), (391, 161), (391, 167), (359, 167)),
    'ENSU_MV1': ((364, 85), (430, 79), (430, 91), (364, 97)),
}


COZ_ENSU = os.path.join(ROOT, 'steam', 'c0data', 'ibg_ensu_win.webp')
COZ_NAME_BOX = (1384, 733, 1512, 757)    # 'neidhardt' row cell in CoZ's 1920x1440 panel (PSP box x4, offset -13,+22)


def ensu_name(path, quad):
    import numpy as np
    img, info = tim2.read(klz.decompress(open(path, 'rb').read()))
    img = img.convert('RGBA').copy()
    src = Image.open(COZ_ENSU).convert('RGBA').crop(COZ_NAME_BOX)
    lum = src.convert('L')
    src = Image.new('RGBA', src.size, (225, 225, 225, 255))
    src.putalpha(lum.point(lambda v: max(0, min(255, (v - 50) * 2))))
    # erase the old name with the row's own colour (sampled just right of it)
    cy = (quad[0][1] + quad[3][1]) // 2
    bgc = img.getpixel((max(p[0] for p in quad) + 4, cy + (quad[2][1] - quad[3][1]) // 2))
    ImageDraw.Draw(img).polygon(quad, fill=bgc)
    xs = [p[0] for p in quad]; ys = [p[1] for p in quad]
    ox, oy = int(min(xs)), int(min(ys))
    region = (int(max(xs)) - ox + 1, int(max(ys)) - oy + 1)
    W, H = src.size
    dst = [(x - ox, y - oy) for x, y in quad]
    A, B = [], []
    for (x, y), (u, v) in zip(dst, [(0, 0), (W, 0), (W, H), (0, H)]):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    coef = np.linalg.solve(np.array(A, float), np.array(B, float))
    warped = src.transform(region, Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)
    mask = Image.new('L', region, 0)
    ImageDraw.Draw(mask).polygon(dst, fill=255)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    layer.paste(warped, (ox, oy), mask)
    img.alpha_composite(layer)
    return klz.compress(tim2.write(img, info))


def ensu_all(ov):
    n = 0
    for name, quad in ENSU_NAME.items():
        p = os.path.join(BGL, name + '.KLZ')
        if os.path.exists(p):
            open(os.path.join(ov, name + '.KLZ'), 'wb').write(ensu_name(p, quad)); n += 1
    return n


if __name__ == '__main__':
    main()
