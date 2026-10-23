"""PSP .P2T texture container.

Header: u32 0x120, u32 0x400, u32 table offset (0x20), u32 count, u32 data base.
Entries (0x40 each): TIM2 picture header (0x30) + ffffffff, blob offset (from base), flag 1, blob size.
Blobs: p2tlz (u32 raw size + LZSS) of pixels followed by CLUT (TIM2 order).

Usage: p2t.py file.P2T outprefix     -> writes outprefix_N.png for each picture
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2tlz, tim2


def entries(b):
    tab, n, base = struct.unpack_from('<III', b, 8)
    out = []
    for i in range(n):
        e = tab + 0x40 * i
        _, off, flag, size = struct.unpack_from('<IIII', b, e + 0x30)
        out.append(dict(hdr=b[e:e + 0x30], off=base + off, flag=flag, size=size))
    return out


def raw(b, e):
    blob = b[e['off']:e['off'] + e['size']]
    return p2tlz.decompress(blob) if e['flag'] else blob


def image(b, e):
    return tim2.read(bytes(16) + e['hdr'] + raw(b, e))


def rebuild(b, new_raw):
    """new_raw: {index: raw TIM2 data bytes (pixels+clut)} -> new P2T bytes (blobs stored LZSS)"""
    tab, n, base = struct.unpack_from('<III', b, 8)
    es = entries(b)
    out = bytearray(b[:base])
    blobs = bytearray()
    for i, e in enumerate(es):
        if i in new_raw:
            blob = p2tlz.compress(new_raw[i]); flag = 1
        else:
            blob = b[e['off']:e['off'] + e['size']]; flag = e['flag']
        off = len(blobs)
        struct.pack_into('<III', out, tab + 0x40 * i + 0x34, off, flag, len(blob))
        blobs += blob
        blobs += bytes(-len(blobs) % 16)
    out += blobs
    out += bytes(-len(out) % 0x800 if len(b) % 0x800 == 0 else 0)
    return bytes(out)


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    for i, e in enumerate(entries(b)):
        img, info = image(b, e)
        img.save('%s_%d.png' % (sys.argv[2], i))
        print(i, info['w'], info['h'], info['bpp'])


def tim2_raw(img, info):
    """RGBA image -> raw P2T picture data (pixels + CLUT) in the entry's original format"""
    return tim2.write(img, info)[len(info['header']):]
