"""PSP CHAOS;HEAD NOAH (ULJM05692) SCENE00 script parser.

Layout: 0x20-byte header, bytecode made of [op u8][len u8][args...] instructions,
followed by a NUL-separated Shift-JIS string pool. Opcode 0x18 displays a line:
  18 10 | u16 ? | u16 ? | u32 string_offset | u32 line_no | u32 ?
"""
import struct


def instructions(b, start, end):
    p = start
    while p < end:
        op, ln = b[p], b[p + 1]
        if ln == 0 or ln & 1 or p + ln > end:
            return
        yield p, op, ln
        p += ln


class Script:
    def __init__(self, data):
        self.b = bytearray(data)
        b = self.b
        # every instruction field that holds a u32 pointing past the code is a string ref
        self.texts = []  # (instr_pos, line_no, str_off)
        offs = set()
        for p, op, ln in self._walk():
            if op == 0x18 and ln == 0x10:
                so, line = struct.unpack_from('<II', b, p + 6)
                if so >= len(b):
                    continue
                self.texts.append((p, line & 0xFFFF, so))
                offs.add(so)
        # choices (0x1B) and effect/log copies (0x23) point at strings placed just before the
        # first dialogue line: the pool starts at the lowest string such a field points to
        for q in self._ptr_fields():
            v = struct.unpack_from('<I', b, q)[0]
            if v < len(b) and (0x81 <= b[v] <= 0x9F or 0xE0 <= b[v] <= 0xEF):
                offs.add(v)
        self.pool_start = min(offs) if offs else len(b)
        self.pool_end = len(b)
        self.refs = self._find_refs()
        # everything after the last referenced string is trailer data: keep it byte-for-byte
        used = [v for q, v in self.refs] + [so for p, l, so in self.texts]
        if used:
            last = max(used)
            self.pool_end = b.index(b'\0', last) + 1

    def _walk(self):
        b = self.b
        entry = struct.unpack_from('<I', b, 0)[0]
        for start in (0x20, entry):
            for p, op, ln in instructions(b, start, len(b)):
                yield p, op, ln

    def strings(self):
        """offset -> raw bytes for every string in the pool"""
        out = {}
        p = self.pool_start
        b = self.b
        end = getattr(self, 'pool_end', len(b))
        while p < end:
            e = b.find(b'\0', p)
            if e < 0:
                break
            if e > p:
                out[p] = bytes(b[p:e])
            p = e + 1
        return out

    # opcode -> offsets of u32 string-pointer fields (all others are numbers, jumps, variables)
    #   0x18 dialogue line, 0x23 effect/log copy, 0xD8/0xD9 movie file name,
    #   0x1B choice list: one pointer per option at +8, +18, +28, ...
    PTR_FIELDS = {0x18: (6,), 0x23: (6,), 0xD8: (2,), 0xD9: (2,)}

    def _ptr_fields(self):
        for p, op, ln in self._walk():
            if op in self.PTR_FIELDS:
                for o in self.PTR_FIELDS[op]:
                    if o + 4 <= ln:
                        yield p + o
            elif op == 0x1B:
                for o in range(8, ln - 3, 10):
                    yield p + o

    def _find_refs(self):
        """(field_pos, str_off) for every string-pointer field that points at a pool string start"""
        starts = set(self.strings())
        refs = []
        seen = set()
        for q in self._ptr_fields():
            if q >= self.pool_start or q in seen:
                continue
            v = struct.unpack_from('<I', self.b, q)[0]
            if v in starts:
                refs.append((q, v)); seen.add(q)
        return refs

    def rebuild(self, new_strings):
        """new_strings: old_offset -> new raw bytes. Returns rebuilt file bytes."""
        b = self.b
        old = self.strings()
        code = bytearray(b[:self.pool_start])
        pool = bytearray()
        remap = {}
        for off in sorted(old):
            remap[off] = self.pool_start + len(pool)
            pool += new_strings.get(off, old[off]) + b'\0'
        for q, v in self.refs:
            struct.pack_into('<I', code, q, remap[v])
        # the original pool may end with NUL padding before the trailer; keep the trailer verbatim
        trailer = bytes(b[self.pool_end:])
        out = code + pool + trailer
        while len(out) % 2:
            out += b'\0'
        return bytes(out)
