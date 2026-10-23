"""Add proportional English glyphs to the PSP message font.

Usage: mkfont.py outdir [ttf] [size]
Writes outdir/DFHSG3W16.FNT, outdir/DFHSG3W16.FNI and work/font.json (encoding map + advances).
Regular glyphs go to SJIS row 0x85, italics to row 0x86 (both unused by the game).
Cell 20x20, 4bpp (high nibble = left pixel), baseline y=14, cap height ~12px like the
existing full-width Latin glyphs.
"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'unpacked', 'DATA0', 'FONTS.AFS.d')
LB = r"C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier"
CELL = 20
BASELINE = 14
CHARS = [chr(c) for c in range(0x21, 0x7F)] + list('’‘“”…—–é·') + [' ', ' ']  # 2-byte narrow / thin space
SPACE_W = 4
THIN_W = 2
TRACK = 1  # extra pixel between glyphs


def sjis_codes(hi):
    for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
        yield bytes([hi, lo])


def glyph_index(code):
    hi, lo = code[0], code[1]
    hi = hi - 0x81 if hi < 0xA0 else hi - 0xC1
    lo = lo - 0x40 if lo < 0x7F else lo - 0x41
    return hi * 188 + lo


def render(font, ch, italic):
    """Native-size hinted rendering. Returns (glyph 20x20 L image, right, advance).
    Engine rule (measured): draws columns [left,right) and advances right-left+spacing."""
    x0, y0, x1, y1 = font.getbbox(ch, anchor='ls')
    adv = font.getlength(ch)
    ox = max(0, -x0)                      # keep left overhang inside the cell
    img = Image.new('L', (CELL + 8, CELL), 0)
    ImageDraw.Draw(img).text((ox, BASELINE), ch, font=font, fill=255, anchor='ls')
    if italic:
        sh = Image.new('L', img.size, 0)
        for y in range(CELL):
            dx = round((BASELINE - y) * 0.18)
            row = img.crop((0, y, img.width, y + 1))
            sh.paste(row, (dx, y))
        img = sh
    bb = img.getbbox()
    if not bb:
        return None, 0, round(adv)
    if italic:
        # slanted ink may pass the advance; keep it (no clipping) but don't add slack
        right = min(CELL, max(round(adv + ox) - 1, bb[2]))
        advance = right
    else:
        right = min(CELL, max(round(adv + ox), bb[2]))
        advance = max(round(adv + ox), 1)
    return img.crop((0, 0, CELL, CELL)), right, advance


def to4bpp(img):
    px = img.load()
    out = bytearray(CELL * CELL // 2)
    for y in range(CELL):
        for x in range(0, CELL, 2):
            a = min(15, (px[x, y] + 8) // 17)
            b = min(15, (px[x + 1, y] + 8) // 17)
            out[(y * CELL + x) // 2] = (a << 4) | b
    return bytes(out)


def main():
    out = sys.argv[1]
    ttf = sys.argv[2] if len(sys.argv) > 2 else os.path.join(LB, 'fonts', 'VL-PGothic-Regular.ttf')
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    font = ImageFont.truetype(ttf, size)
    fnt = bytearray(open(os.path.join(SRC, 'DFHSG3W16.FNT'), 'rb').read())
    fni = bytearray(open(os.path.join(SRC, 'DFHSG3W16.FNI'), 'rb').read())
    fmap = {'custom': True, 'regular': {}, 'italic': {}, 'width': {}, 'iwidth': {}}
    # The engine draws a single ASCII byte b (0x21..0x7E) with glyph 752 + (b - 0x21), i.e. row 0x85 in
    # ASCII order, and a single 0x20 with glyph 751 (code 0x84FC). Keep that order so English can be
    # stored as plain 1-byte ASCII; extras (curly quotes, dashes...) follow and use 2-byte codes.
    gi = 751
    fnt[gi * 200:(gi + 1) * 200] = bytes(200)
    fni[gi * 4:gi * 4 + 4] = bytes([0, SPACE_W, 0, 0])
    fmap['ascii_space'] = SPACE_W
    for row, italic, key, wkey in ((0x85, False, 'regular', 'width'), (0x86, True, 'italic', 'iwidth')):
        codes = sjis_codes(row)
        fmap[wkey][' '] = SPACE_W
        for ch in CHARS:
            code = next(codes)
            gi = glyph_index(code)
            if ch in (' ', ' '):
                sw = SPACE_W if ch == ' ' else THIN_W      # thin space: only for pages that need the room
                fnt[gi * 200:(gi + 1) * 200] = bytes(200)
                fni[gi * 4:gi * 4 + 4] = bytes([0, sw, 0, 0])
                fmap[key][ch] = code.hex(); fmap[wkey][ch] = sw
                continue
            g, right, advance = render(font, ch, italic)
            if g is None:
                continue
            fnt[gi * 200:(gi + 1) * 200] = to4bpp(g)
            # FNI: left, right (exclusive), spacing -> advance = right - left + spacing
            spacing = max(0, advance - right)
            fni[gi * 4:gi * 4 + 4] = bytes([0, right, spacing, 0])
            fmap[key][ch] = code.hex()
            fmap[wkey][ch] = right + spacing
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'DFHSG3W16.FNT'), 'wb').write(fnt)
    open(os.path.join(out, 'DFHSG3W16.FNI'), 'wb').write(fni)
    json.dump(fmap, open(os.path.join(ROOT, 'work', 'font.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('glyphs', len(fmap['regular']), len(fmap['italic']))


if __name__ == '__main__':
    main()
