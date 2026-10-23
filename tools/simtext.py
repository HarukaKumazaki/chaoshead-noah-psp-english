"""Render PSP-encoded text exactly like the engine (columns [left,right), advance right-left+spacing)."""
import sys, os
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc
from mkfont import glyph_index

def render(lines, fnt, fni, scale=3):
    W, H = 480, 24 * len(lines) + 8
    img = Image.new('L', (W, H), 30)
    for li, t in enumerate(lines):
        b = enc.encode(t); x = 8; y = 4 + li * 24; i = 0
        while i < len(b):
            if b[i] == 0x20:
                gi = 751; i += 1
            elif 0x21 <= b[i] <= 0x7E:
                gi = 752 + b[i] - 0x21; i += 1
            elif b[i] < 0x80:
                i += 1; continue
            else:
                gi = glyph_index(b[i:i + 2]); i += 2
            l, r, sp = fni[gi * 4], fni[gi * 4 + 1], fni[gi * 4 + 2]
            g = fnt[gi * 200:gi * 200 + 200]
            for yy in range(20):
                for xx in range(l, r):
                    v = g[(yy * 20 + xx) // 2]; v = (v >> 4) if xx % 2 == 0 else (v & 15)
                    if v and 0 <= x + xx - l < W: img.putpixel((x + xx - l, y + yy), 30 + v * 15)
            x += r - l + sp
    return img.resize((W * scale, H * scale), Image.NEAREST)

if __name__ == '__main__':
    d = sys.argv[1]
    fnt = open(os.path.join(d, 'DFHSG3W16.FNT'), 'rb').read(); fni = open(os.path.join(d, 'DFHSG3W16.FNI'), 'rb').read()
    lines = sys.argv[3:]
    render(lines, fnt, fni).save(sys.argv[2])
