"""KLZ codec (CHAOS;HEAD NOAH PSP), reimplemented from the EBOOT routine at 0x088EA390.

Container: u32 BE total size, then chunks until total is reached:
  u16 BE header; bit15 set -> 0x4000 raw bytes follow (header&0x7fff bytes in stream)
                 else       -> header = compressed length of an LZ chunk (<= 0x4000 out)
LZ chunk: flag byte, bits LSB-first; 1 = back-reference (2 bytes BE: len = (v&0x1f)+3,
dist = (v>>5)+1, relative to the chunk start), 0 = literal byte.
Usage: klz.py d in.KLZ out.bin | klz.py c in.bin out.KLZ
"""
import struct, sys

CHUNK = 0x4000


def _dechunk(src, n):
    out = bytearray()
    p = 1
    flags = src[0]
    bit = 0
    consumed = 1
    while consumed < n - 0 and p < len(src):
        if flags & (1 << bit):
            v = (src[p] << 8) | src[p + 1]
            p += 2; consumed += 2
            ln = (v & 0x1F) + 3
            s = (len(out) - (v >> 5) - 1) & 0xFFFF
            for _ in range(ln):
                if len(out) < 0x800 and len(out) < s:
                    out.append(out[0] if out else 0)
                else:
                    out.append(out[s])
                s = (s + 1) & 0xFFFF
        else:
            out.append(src[p]); p += 1; consumed += 1
        bit += 1
        if bit == 8:
            if consumed >= n:
                break
            flags = src[p]; p += 1; consumed += 1; bit = 0
    return bytes(out)


def decompress(b):
    total = struct.unpack_from('>I', b, 0)[0]
    p = 4
    out = bytearray()
    while len(out) < total:
        h = struct.unpack_from('>H', b, p)[0]; p += 2
        if h & 0x8000:
            ln = h & 0x7FFF
            out += b[p:p + CHUNK]
            p += ln
        else:
            out += _dechunk(b[p:p + h], h)
            p += h
    return bytes(out[:total])


def _comp_chunk(data):
    out = bytearray()
    i = 0
    n = len(data)
    head = {}
    while i < n:
        flag_pos = len(out); out.append(0)
        for bit in range(8):
            if i >= n:
                break
            best_len, best_d = 0, 0
            if i + 3 <= n:
                key = data[i:i + 3]
                for j in reversed(head.get(key, [])[-64:]):
                    d = i - j
                    if d > 2048:
                        break
                    l = 0
                    while l < 34 and i + l < n and data[j + l] == data[i + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_d = l, d
                        if l == 34:
                            break
            if best_len >= 3:
                v = ((best_d - 1) << 5) | (best_len - 3)
                out += bytes([v >> 8, v & 0xFF])
                out[flag_pos] |= 1 << bit
                step = best_len
            else:
                out.append(data[i]); step = 1
            for k in range(i, min(i + step, n - 2)):
                head.setdefault(data[k:k + 3], []).append(k)
            i += step
    return bytes(out)


def compress(data):
    out = bytearray(struct.pack('>I', len(data)))
    for o in range(0, len(data), CHUNK):
        chunk = data[o:o + CHUNK]
        c = _comp_chunk(chunk)
        if len(c) >= len(chunk) or len(c) >= 0x8000:
            out += struct.pack('>H', 0x8000 | len(chunk)) + chunk.ljust(CHUNK, b'\0')[:len(chunk)]
        else:
            out += struct.pack('>H', len(c)) + c
    return bytes(out)


if __name__ == '__main__':
    mode, a, b = sys.argv[1:4]
    data = open(a, 'rb').read()
    open(b, 'wb').write(decompress(data) if mode == 'd' else compress(data))
