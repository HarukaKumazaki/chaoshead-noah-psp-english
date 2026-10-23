"""Replace NUL-terminated Shift-JIS strings inside a binary (menu scripts, tables).

patch(data, tr, refs='u32'|'u16'|'both', table_end=None) -> new bytes
  tr: {japanese unicode string: english unicode string (PSP markup allowed)}
A replacement that fits the original slot (string + its NUL padding) is written in place;
otherwise it is appended at the end of the file and every reference to the old offset is
repointed. u32 references are searched over the whole file at even offsets, u16 references
only below table_end (offset tables at the top of some files).
"""
import struct, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc

SJ = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')


def strings(b):
    """offset -> (bytes, slot_len) for NUL-terminated strings that start right after a NUL"""
    out = {}
    for m in SJ.finditer(b):
        s, e = m.start(), m.end()
        if s == 0 or b[s - 1] != 0 or e >= len(b) or b[e] != 0:
            continue
        end = e + 1
        while end < len(b) and b[end] == 0:
            end += 1
        out[s] = (b[s:e], end - s)
    return out


def patch_seq(data, start, fn):
    """Index-addressed string list from `start` to EOF: rebuild in the same order/count.
    fn(japanese) -> english or None."""
    parts = data[start:].split(b'\0')
    n = 0
    for i, p in enumerate(parts):
        try:
            t = p.decode('cp932')
        except UnicodeDecodeError:
            continue
        e = fn(t) if p else None
        if e:
            parts[i] = enc.encode(e); n += 1
    return data[:start] + b'\0'.join(parts), n


def patch(data, tr, refs='u32', table_end=None, align=4):
    b = bytearray(data)
    st = strings(bytes(b))
    todo = []
    for off, (raw, slot) in st.items():
        try:
            t = raw.decode('cp932')
        except UnicodeDecodeError:
            continue
        v = tr.get(off, tr.get(t))         # per-offset translation wins; bytes are written raw
        if v is not None:
            todo.append((off, slot, (v if isinstance(v, bytes) else enc.encode(v)) + b'\0'))
    applied = 0
    for off, slot, new in todo:
        if len(new) <= slot:
            b[off:off + slot] = new.ljust(slot, b'\0')
            applied += 1
            continue
        while len(b) % align:
            b.append(0)
        noff = len(b)
        b += new
        hits = 0
        if refs in ('u32', 'both'):
            for p in range(0, len(data) - 3, 2):
                if struct.unpack_from('<I', data, p)[0] == off:
                    struct.pack_into('<I', b, p, noff); hits += 1
        if refs in ('u16', 'both') and noff < 0x10000 and hits == 0:
            ps = [p for p in range(0, (table_end or len(data)) - 1, 2)
                  if struct.unpack_from('<H', data, p)[0] == off]
            if len(ps) != 1:
                raise ValueError('ambiguous u16 refs for string at %#x: %s' % (off, [hex(p) for p in ps]))
            struct.pack_into('<H', b, ps[0], noff); hits += 1
        if hits == 0:
            raise ValueError('no reference found for string at %#x' % off)
        applied += 1
    return bytes(b), applied, len(todo)
