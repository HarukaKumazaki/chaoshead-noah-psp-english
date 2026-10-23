"""TIM2 (as used inside KLZ) read/write for 4bpp/8bpp paletted images with CSM1 palette order."""
import struct
from PIL import Image


def _csm1(pal):
    if len(pal) != 256:
        return list(pal)
    p = list(pal)
    for i in range(0, 256, 32):
        p[i + 8:i + 16], p[i + 16:i + 24] = pal[i + 16:i + 24], pal[i + 8:i + 16]
    return p


def read(b):
    tot, cs, isz, hs, cn, fmt, mm, ct, it, w, h = struct.unpack_from('<IIIHHBBBBHH', b, 16)
    p = 16 + hs
    data = b[p:p + isz]
    clut = b[p + isz:p + isz + cs]
    pal = _csm1([tuple(clut[i * 4:i * 4 + 4]) for i in range(cs // 4)])
    if it != 5:   # 4bpp: low nibble is the left pixel
        data = bytes(v for byte in data for v in (byte & 0xF, byte >> 4))
    img = Image.frombytes('P', (w, h), bytes(data[:w * h]))
    flat = []
    for r, g, bb, a in pal:
        flat += [r, g, bb, min(255, a * 2)]
    img.putpalette(flat + [0] * (1024 - len(flat)), 'RGBA')
    # data after the picture (e.g. a sprite's face/lip patches, which index this picture's CLUT)
    rgba = img.convert('RGBA')
    import numpy as np
    a = np.asarray(rgba)
    t = a[a[:, :, 3] == 0][:, :3]
    clear = tuple(int(v) for v in np.median(t, 0)) if len(t) else None
    return rgba, dict(w=w, h=h, bpp=8 if it == 5 else 4, header=b[:16 + hs], clear=clear,
                                     clut=bytes(clut), tail=bytes(b[16 + tot:]))


def _pad(data, info):
    """pixel data padded to the image size stored in the header (rows can be padded, e.g. 120x125)"""
    import struct
    isz = struct.unpack_from('<I', info['header'], 24)[0]
    return data + bytes(max(0, isz - len(data)))


def write(img, info):
    """img RGBA -> TIM2 bytes with the same header/format as the original; trailing data is kept, and
    when there is any (patches drawn with this CLUT) the original palette is kept too"""
    w, h, bpp = info['w'], info['h'], info['bpp']
    if info.get('clear') is not None:          # invisible pixels keep the original's colour (filter edges)
        import numpy as np
        a = np.asarray(img.convert('RGBA')).copy()
        a[a[:, :, 3] == 0, :3] = info['clear']
        img = Image.fromarray(a)
    if info.get('tail'):
        return _write_fixed_palette(img, info)
    ncol = 256 if bpp == 8 else 16
    q = img.convert('RGBA').quantize(ncol, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = q.getpalette('RGBA')[:ncol * 4]
    pal += [0] * (ncol * 4 - len(pal))
    entries = [tuple(pal[i * 4:i * 4 + 4]) for i in range(ncol)]
    entries = [(r, g, b, (a + 1) // 2) for r, g, b, a in entries]   # PS2 alpha 0..128
    idx = list(q.getdata())
    if bpp == 8:
        data = bytes(idx)
    else:
        data = bytes((idx[i] & 0xF) | ((idx[i + 1] & 0xF) << 4) for i in range(0, len(idx), 2))
    clut = b''.join(bytes(e) for e in _csm1(entries))
    return info['header'] + _pad(data, info) + clut


def _write_fixed_palette(img, info):
    import numpy as np
    w, h, bpp = info['w'], info['h'], info['bpp']
    clut = info['clut']
    n = len(clut) // 4
    pal = _csm1([tuple(clut[i * 4:i * 4 + 4]) for i in range(n)])          # index -> colour
    P = np.array([(r, g, b, min(255, a * 2)) for r, g, b, a in pal], dtype=np.int32)
    A = np.asarray(img.convert('RGBA'), dtype=np.int32).reshape(-1, 4)
    idx = np.empty(len(A), dtype=np.uint8)
    for s0 in range(0, len(A), 4096):
        blk = A[s0:s0 + 4096]
        d = ((blk[:, None, :3] - P[None, :, :3]) ** 2).sum(-1) + 4 * (blk[:, None, 3] - P[None, :, 3]) ** 2
        idx[s0:s0 + 4096] = d.argmin(1)
    if bpp == 8:
        data = idx.tobytes()
    else:
        data = bytes((idx[i] & 0xF) | ((idx[i + 1] & 0xF) << 4) for i in range(0, len(idx), 2))
    return info['header'] + _pad(data, info) + clut + info['tail']
