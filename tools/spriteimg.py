"""CoZ's edited character sprites (English sign text etc.) -> PSP CHL sprites.

CoZ ships tile atlases (.webp) + meshes (_.mvl): 'MVL1', count, then 0x40-byte entries at 0x60
(+0x10 vertex count, +0x14 vertex array offset, +0x18 index count, +0x1C index offset, +0x20 name);
vertices are (x, y, z, u, v) floats, indices u16 triangles (pairs form axis-aligned tile quads).
The base part is reconstructed, scaled/aligned onto every PSP pose of that outfit, and only the
pixels CoZ changed (their edit region) are pasted, so the PSP faces/expressions stay untouched.

Usage: spriteimg.py ovroot
"""
import os, sys, struct, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageFilter
import klz, tim2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C0 = os.path.join(ROOT, 'steam', 'c0data')
CHL = os.path.join(ROOT, 'unpacked', 'DATA0', 'CHL00.AFS.d')


def mvl_parts(path):
    d = open(path, 'rb').read()
    n = struct.unpack_from('<I', d, 4)[0]
    parts = {}
    for i in range(n):
        e = 0x60 + 0x40 * i
        vc, vo, ic, io = struct.unpack_from('<4I', d, e + 0x10)
        name = d[e + 0x20:e + 0x40].split(b'\0')[0].decode()
        verts = [struct.unpack_from('<5f', d, vo + 20 * k) for k in range(vc)]
        idx = struct.unpack_from('<%dH' % ic, d, io)
        parts[name] = (verts, idx)
    return parts


def render(atlas_path, mvl_path, part_suffixes=('', 'L1', 'E1')):
    atlas = Image.open(atlas_path).convert('RGBA')
    W, H = atlas.size
    parts = mvl_parts(mvl_path)
    base = min(parts, key=len)
    quads = []
    for suf in part_suffixes:
        if base + suf not in parts:
            continue
        verts, idx = parts[base + suf]
        for t in range(0, len(idx) - 2, 3):
            quads.append([(verts[i][0], verts[i][1], verts[i][3] * W, verts[i][4] * H) for i in idx[t:t + 3]])
    x0 = min(v[0] for q in quads for v in q); y0 = min(v[1] for q in quads for v in q)
    x1 = max(v[0] for q in quads for v in q); y1 = max(v[1] for q in quads for v in q)
    out = Image.new('RGBA', (int(round(x1 - x0)), int(round(y1 - y0))), (0, 0, 0, 0))
    for tri in quads:
        # affine dest(x, y) -> atlas(u, v) from the triangle's three vertices
        A = np.array([[v[0] - x0, v[1] - y0, 1] for v in tri])
        try:
            cu = np.linalg.solve(A, [v[2] for v in tri]); cv = np.linalg.solve(A, [v[3] for v in tri])
        except np.linalg.LinAlgError:
            continue
        bx0 = int(np.floor(min(v[0] for v in tri) - x0)); by0 = int(np.floor(min(v[1] for v in tri) - y0))
        bx1 = int(np.ceil(max(v[0] for v in tri) - x0)); by1 = int(np.ceil(max(v[1] for v in tri) - y0))
        w, h = bx1 - bx0, by1 - by0
        if w <= 0 or h <= 0:
            continue
        coeffs = (cu[0], cu[1], cu[0] * bx0 + cu[1] * by0 + cu[2], cv[0], cv[1], cv[0] * bx0 + cv[1] * by0 + cv[2])
        tile = atlas.transform((w, h), Image.AFFINE, coeffs, resample=Image.BILINEAR)
        mask = Image.new('L', (w, h), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).polygon([(v[0] - x0 - bx0, v[1] - y0 - by0) for v in tri], fill=255)
        region = out.crop((bx0, by0, bx1, by1))
        region.paste(tile, (0, 0), mask)
        out.paste(region, (bx0, by0))
    return out




SCALES = np.arange(0.15, 0.45, 0.0025)


def align(coz, psp):
    """best (scale, dx, dy) placing coz (scaled) onto psp, by masked RGB error over the face area"""
    P = np.asarray(psp.convert('RGBA')).astype(float)
    best = None
    pa = P[:, :, 3] > 200
    ys, xs = np.nonzero(pa)
    ptop, pl, pr = ys.min(), xs.min(), xs.max()
    C0a = np.asarray(coz)[:, :, 3] > 200
    cys, cxs = np.nonzero(C0a)
    for s in SCALES:
        w, h = int(round(coz.width * s)), int(round(coz.height * s))
        c = np.asarray(coz.resize((w, h), Image.LANCZOS)).astype(float)
        ctop = int(round(cys.min() * s))
        dy0 = ptop - ctop
        for dy in range(dy0 - 3, dy0 + 4):
            for dx in range(-int(w), psp.width, 1):
                pass
            # horizontal: match the hair/face band
            band = slice(max(0, dy), min(psp.height, dy + h))
            break
        # brute horizontal search on a face band
        y_a, y_b = ptop + 5, ptop + 60
        if y_b - dy > h or y_a - dy < 0:
            continue
        crow = c[y_a - dy:y_b - dy]
        for dx in range(pl - w, pr + 1):
            xa, xb = max(0, dx), min(psp.width, dx + w)
            if xb - xa < 40:
                continue
            pc = P[y_a:y_b, xa:xb]; cc = crow[:, xa - dx:xb - dx]
            m = (pc[:, :, 3] > 200) & (cc[:, :, 3] > 200)
            if m.sum() < 500:
                continue
            e = np.abs(pc[:, :, :3] - cc[:, :, :3]).sum(2)[m].mean()
            if best is None or e < best[0]:
                best = (e, s, dx, dy)
    return best


def paper(px):
    return (px[..., :3].min(-1) > 165) & (px[..., :3].max(-1) - px[..., :3].min(-1) < 30)


def sign_sprite(coz, psp):
    """paste CoZ's sign (everything from the sign's top edge down) onto the PSP pose; rows the CoZ
    mesh does not reach keep the PSP pixels with their ink painted over in paper colour"""
    e, s, dx, dy = align(coz, psp)
    c = coz.resize((round(coz.width * s), round(coz.height * s)), Image.LANCZOS)
    lay = Image.new('RGBA', psp.size, (0, 0, 0, 0)); lay.paste(c, (dx, dy), c)
    L = np.asarray(lay).copy(); P = np.asarray(psp.convert('RGBA')).copy()
    H = P.shape[0]
    pap = paper(L) & (L[..., 3] > 200)
    rows = [y for y in range(H // 3, H) if pap[y].sum() >= 40]
    top = rows[0] - 2
    cov = min(H, dy + c.height) - 1                     # last row the CoZ mesh covers
    out = P.copy()
    m = (L[..., 3] > 0)
    m[:top] = False
    out[m] = L[m]
    band = L[max(top, cov - 12):cov]
    if cov < H - 1 and (paper(band) & (band[..., 3] > 200)).any():   # sign continues below: blank paper
        band = L[max(top, cov - 12):cov]
        pp = paper(band) & (band[..., 3] > 200)
        xs = np.nonzero(pp.any(0))[0]
        x0, x1 = xs.min(), xs.max()
        for x in range(x0, x1 + 1):
            win = band[:, max(x0, x - 15):x + 16][pp[:, max(x0, x - 15):x + 16]]
            if not len(win):
                continue
            col = np.median(win, axis=0).astype(np.uint8)
            for y in range(cov, H):
                # keep the hands / jacket (non-paper, non-ink skin or cloth) of the PSP art
                px = P[y, x].astype(int)
                jacket = px[1] > px[0] + 12 and px[:3].max() < 150          # green coat sleeve
                skin = px[0] > 180 and px[1] > 130 and px[0] > px[2] + 40 and px[1] > px[2] + 15
                if px[3] > 200 and not jacket and not skin:
                    out[y, x] = col
    return Image.fromarray(out), (round(e, 1), round(s, 4), dx, dy, top, cov)


# CoZ edits limited to one area of an outfit (English text on badges/emblems):
# CoZ sprite -> box in CoZ-render fractions; applied to every PSP expression of that outfit
REGION_EDITS = {
    'shi_l1a': (0.60, 0.55, 0.82, 0.70), 'shi_l2a': (0.60, 0.55, 0.82, 0.70),     # nurse ID badge
    'shi_s1a': (0.50, 0.27, 0.86, 0.41), 'shi_s2a': (0.50, 0.27, 0.86, 0.41),
    'sen_l1g': (0.55, 0.62, 0.68, 0.78), 'sen_s1g': (0.50, 0.32, 0.74, 0.47),     # SUIMEI crest
}


def region_edit(coz, psp, box, al):
    e, s, dx, dy = al
    W, H = coz.size
    c = coz.resize((round(W * s), round(H * s)), Image.LANCZOS)
    lay = Image.new('RGBA', psp.size, (0, 0, 0, 0)); lay.paste(c, (dx, dy), c)
    L = np.asarray(lay); P = np.asarray(psp.convert('RGBA')).copy()
    x0 = int(box[0] * W * s + dx); y0 = int(box[1] * H * s + dy)
    x1 = int(box[2] * W * s + dx); y1 = int(box[3] * H * s + dy)
    sub = (slice(max(0, y0), min(P.shape[0], y1)), slice(max(0, x0), min(P.shape[1], x1)))
    m = (L[sub][..., 3] > 200) & (P[sub][..., 3] > 200)
    P[sub][m] = L[sub][m]
    return Image.fromarray(P)


def main():
    od = os.path.join(sys.argv[1], 'DATA0', 'CHL00.AFS.d'); os.makedirs(od, exist_ok=True)
    for n, box in REGION_EDITS.items():
        coz = render(os.path.join(C0, n + '.webp'), os.path.join(C0, n + '_.mvl'))
        fs = sorted(glob.glob(os.path.join(CHL, n.upper() + '_*.KLZ')))
        if not fs:
            continue
        al = align(coz, tim2.read(klz.decompress(open(fs[0], 'rb').read()))[0])
        print(n, 'align', round(al[0], 1), round(al[1], 4), al[2], al[3], flush=True)
        for f in fs:
            psp, info = tim2.read(klz.decompress(open(f, 'rb').read()))
            img = region_edit(coz, psp, box, al)
            open(os.path.join(od, os.path.basename(f)), 'wb').write(klz.compress(tim2.write(img, info)))
    for n in ('kaz_l1c', 'kaz_l1d', 'kaz_l1e', 'kaz_s1c', 'kaz_s1d', 'kaz_s1e'):
        coz = render(os.path.join(C0, n + '.webp'), os.path.join(C0, n + '_.mvl'))
        for f in sorted(glob.glob(os.path.join(CHL, n.upper() + '_*.KLZ'))):
            psp, info = tim2.read(klz.decompress(open(f, 'rb').read()))
            img, st = sign_sprite(coz, psp)
            open(os.path.join(od, os.path.basename(f)), 'wb').write(klz.compress(tim2.write(img, info)))
            print(os.path.basename(f), st, flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'show':
        render(os.path.join(C0, sys.argv[2] + '.webp'), os.path.join(C0, sys.argv[2] + '_.mvl')).save(sys.argv[3])
    else:
        main()
