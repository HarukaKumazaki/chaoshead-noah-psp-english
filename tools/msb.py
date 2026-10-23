"""MAGES .msb (MES) reader for the CoZ CHAOS;HEAD NOAH patch.
Usage: msb.py file.msb [count]"""
import json, struct, sys, os

STEAM = os.environ.get('CHN_STEAM_DIR', r"C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH")
LB = os.path.join(STEAM, 'languagebarrier')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def en_file(name):
    """English .msb by file name. CoZ's patchdef redirects mes01 to c0mes01, so that is the text the
    patch shows; steam/mes01 (languagebarrier/mes01.cpk) is the fallback"""
    for d in ('c0mes01', 'mes01'):
        p = os.path.join(ROOT, 'steam', d, name)
        if os.path.exists(p):
            return p
    return os.path.join(ROOT, 'steam', 'mes01', name)


CH = json.load(open(os.path.join(LB, 'patchdef.json'), encoding='utf-8'))['base']['charset']
_ext = json.load(open(os.path.join(LB, 'chaos_head_noah-extended.json'), encoding='utf-8'))
# glyph ids beyond the base charset: italic-only glyphs are wrapped in ..
EXT = {}
for _k, _v in _ext.items():
    _i = int(_k, 16)
    if _i >= len(CH):
        EXT[_i] = ('%s' % _v['text']) if _v.get('italic') and not _v.get('regular') else _v['text']

# control codes: 00 newline, 01 name start, 02 name end/line start, 03 end of page,
# 08/18 present, 11 xx xx (line meta, 2 arg bytes), 07 xx (pause/wait), ff terminator
ARGS = {0x11: 2, 0x07: 1, 0x19: 2, 0x12: 2}
EXPR = {0x04}  # color: followed by an SC3 expression


def tokens(b):
    p = 0
    while p < len(b):
        c = b[p]
        if c == 0xFF:
            return
        if c >= 0x80:
            yield ('g', ((c & 0x7F) << 8) | b[p + 1]); p += 2
        elif c in EXPR:
            # SC3 expression terminated by 0x00; literal tokens (>=0x80) carry 0/1/2/4 extra bytes
            q = p + 1
            while q < len(b) and b[q] != 0x00:
                t = b[q]; q += 1
                if t & 0x80:
                    q += (0, 1, 2, 4)[(t >> 5) & 3]
            q += 1
            if c == 0x04 and q < len(b) and b[q] == 0x00:
                q += 1  # color expressions end with 00 00
            yield ('c', c, b[p + 1:q - 1].rstrip(b'\x00')); p = q
        else:
            n = ARGS.get(c, 0)
            yield ('c', c, b[p + 1:p + 1 + n]); p += 1 + n


def dec(b, show_ctrl=True):
    out = []
    for t in tokens(b):
        if t[0] == 'g':
            g = t[1]
            out.append(CH[g] if g < len(CH) else EXT.get(g, '<%d>' % g))
        else:
            c = t[1]
            if c == 0x00: out.append('\n')
            elif c == 0x01: out.append('[')
            elif c == 0x02: out.append(']')
            elif show_ctrl: out.append('{%02x%s}' % (c, t[2].hex()))
    return ''.join(out)


def mes(path):
    b = open(path, 'rb').read()
    n, doff = struct.unpack_from('<II', b, 8)
    ents = [struct.unpack_from('<II', b, 16 + 8 * i) for i in range(n)]
    return [(i, b[doff + o:]) for i, o in ents]


if __name__ == '__main__':
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    for i, raw in mes(sys.argv[1])[:lim]:
        print(i, repr(dec(raw)))
