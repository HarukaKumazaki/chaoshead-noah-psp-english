"""Catalogue every text string the EBOOT references, with all of its references.

Writes work/eboot/catalog.json: [{off, text, slot, words:[fileoff], code:[[lui_off, lo_off]]}]
A string start is any address that a 32-bit data word or a lui/addiu|ori pair points at and
where Shift-JIS text begins. slot = bytes up to the next referenced string or non-zero data.
"""
import struct, json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ebootrefs as E

B = E.B
DATA_LO, DATA_HI = 0x104000, len(B)
SJ = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\x20-\x7e\n])+\x00')
HAS_JP = re.compile(rb'[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]')


def in_data(v):
    f = E.fo(v)
    return DATA_LO <= f < DATA_HI


def all_refs():
    words, code = {}, {}
    for p in range(E.OFF, len(B) - 3, 4):
        v = struct.unpack_from('<I', B, p)[0]
        if 0x08804000 <= v < 0x08804000 + len(B) and in_data(v):
            words.setdefault(E.fo(v), []).append(p)
    lui = {}
    for p in range(E.OFF, E.OFF + E.TEXT_END, 4):
        w = struct.unpack_from('<I', B, p)[0]
        op = w >> 26
        if op == 0x0F:
            lui[(w >> 16) & 31] = (p, w & 0xFFFF)
        elif op in (0x09, 0x0D):
            rs = (w >> 21) & 31
            if rs in lui and p - lui[rs][0] < 0x100:
                hi, lo = lui[rs][1], w & 0xFFFF
                v = ((hi << 16) + (lo - 0x10000 if op == 0x09 and lo & 0x8000 else lo)) & 0xFFFFFFFF
                if in_data(v):
                    code.setdefault(E.fo(v), []).append((lui[rs][0], p))
    return words, code


def main():
    words, code = all_refs()
    starts = sorted(set(words) | set(code))
    items = []
    for f in starts:
        m = SJ.match(B, f)
        if not m or not HAS_JP.search(m.group()):
            continue
        try:
            t = m.group()[:-1].decode('cp932')
        except UnicodeDecodeError:
            continue
        items.append(dict(off=f, text=t, words=words.get(f, []), code=code.get(f, [])))
    offs = [i['off'] for i in items]
    for k, i in enumerate(items):
        # only the string, its NUL and the padding up to the next 4-byte boundary are reusable:
        # zero bytes further on can be initialized variables living in the same section
        end = i['off'] + len(i['text'].encode('cp932')) + 1
        lim = offs[k + 1] if k + 1 < len(offs) else end + 3
        while end < lim and end % 4 != 0 and B[end] == 0:
            end += 1
        i['slot'] = end - i['off']
    os.makedirs(os.path.join(E.__dict__.get('ROOT', '.'), 'work', 'eboot'), exist_ok=True)
    json.dump(items, open('work/eboot/catalog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('strings', len(items), 'unique', len(set(i['text'] for i in items)),
          'bytes', sum(i['slot'] for i in items))


if __name__ == '__main__':
    main()
