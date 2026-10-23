"""Find references to EBOOT data addresses: (a) 32-bit words in data, (b) lui/addiu|ori pairs in code."""
import struct, re, sys
B = open('work/eboot/EBOOT_dec.ELF', 'rb').read()
OFF, BASE = 0x54, 0x08804000
TEXT_END = 0x104000  # code size (approx; data follows)

def va(fo): return BASE + fo - OFF
def fo(v): return v - BASE + OFF

def word_refs(target):
    t = struct.pack('<I', target)
    return [m.start() for m in re.finditer(re.escape(t), B) if m.start() % 4 == OFF % 4]

def code_refs(target):
    hi = (target + 0x8000) >> 16; lo = target & 0xFFFF
    out = []
    lui = {}
    for p in range(OFF, OFF + TEXT_END, 4):
        w = struct.unpack_from('<I', B, p)[0]
        op = w >> 26
        if op == 0x0F:  # lui
            lui[(w >> 16) & 31] = (p, w & 0xFFFF)
        elif op in (0x09, 0x0D):  # addiu / ori
            rs = (w >> 21) & 31
            if rs in lui and lui[rs][1] == (hi if op == 0x09 else target >> 16) and (w & 0xFFFF) == lo:
                if p - lui[rs][0] < 0x100:
                    out.append((lui[rs][0], p))
    return out

if __name__ == '__main__':
    for a in sys.argv[1:]:
        f = int(a, 16); v = va(f)
        print(hex(f), hex(v), 'words', [hex(x) for x in word_refs(v)], 'code', [(hex(a), hex(b)) for a, b in code_refs(v)])
