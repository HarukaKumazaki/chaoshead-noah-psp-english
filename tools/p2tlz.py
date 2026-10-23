"""P2T blob compression: LE u32 raw size + Okumura LZSS (4 KB zero-filled ring, start 0xFEE,
flag byte LSB first, 1 = literal, ref = 12-bit ring position + 4-bit length-3)."""
import struct


def decompress(blob):
    n = struct.unpack_from('<I', blob)[0]
    src = blob[4:]
    win = bytearray(4096); r = 0xFEE; out = bytearray(); i = 0; flags = 0
    while len(out) < n and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xff00; i += 1
            if i >= len(src):
                break
        if flags & 1:
            c = src[i]; i += 1; out.append(c); win[r] = c; r = (r + 1) & 0xfff
        else:
            if i + 1 >= len(src):
                break
            a, b = src[i], src[i + 1]; i += 2
            off = a | ((b & 0xf0) << 4)
            for k in range((b & 0xf) + 3):
                c = win[(off + k) & 0xfff]; out.append(c); win[r] = c; r = (r + 1) & 0xfff
    out += bytes(n - len(out))
    return bytes(out[:n])


def compress(data):
    """greedy LZSS encoder compatible with decompress (hash chains over the 4 KB ring)"""
    n = len(data)
    out = bytearray(struct.pack('<I', n))
    # ring position of data index j is (0xFEE + j) & 0xfff; positions before data start are zeros
    heads = {}
    i = 0
    while i < n:
        flagpos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_src = 0, 0
            maxl = min(18, n - i)
            if maxl >= 3:
                key = data[i:i + 3]
                for j in reversed(heads.get(key, ())):
                    if i - j > 4096 - 18:
                        break
                    l = 3
                    while l < maxl and data[j + l] == data[i + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_src = l, j
                        if l == maxl:
                            break
                # zero run from the pre-filled ring (only valid while the ring still holds zeros)
                if best_len < maxl and i < 4096 - 18 - 18:
                    z = 0
                    while z < maxl and data[i + z] == 0:
                        z += 1
                    if z > best_len and z >= 3:
                        best_len, best_src = z, -18
            if best_len >= 3:
                pos = (0xFEE + best_src) & 0xfff
                out += bytes((pos & 0xff, ((pos >> 4) & 0xf0) | (best_len - 3)))
                step = best_len
            else:
                flags |= 1 << bit
                out.append(data[i]); step = 1
            for k in range(i, i + step):
                if k + 3 <= n:
                    lst = heads.setdefault(data[k:k + 3], [])
                    lst.append(k)
                    if len(lst) > 64:
                        del lst[:32]
            i += step
        out[flagpos] = flags
    return bytes(out)


def _tokens(blob):
    """original stream -> [(out_index, 'lit', byte) | (out_index, 'ref', b0, b1, length)]"""
    n = struct.unpack_from('<I', blob)[0]
    src = blob[4:]; i = 0; flags = 0; outn = 0; toks = []
    while outn < n and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xff00; i += 1
        if flags & 1:
            toks.append((outn, 'lit', src[i])); i += 1; outn += 1
        else:
            a, b = src[i], src[i + 1]; i += 2
            L = (b & 0xf) + 3
            toks.append((outn, 'ref', a, b, L)); outn += L
    return toks


def compress_keep_prefix(orig_blob, data, keep):
    """encode data, reusing orig_blob's own tokens for the first `keep` bytes (which must be identical
    in both). The game's decoder handles the original encoder's streams; this keeps unchanged
    regions byte-for-byte in the original encoding and only re-encodes the rest."""
    toks = []
    for t in _tokens(orig_blob):
        end = t[0] + (1 if t[1] == 'lit' else t[4])
        if end > keep:
            break
        toks.append(t)
    start = toks[-1][0] + (1 if toks[-1][1] == 'lit' else toks[-1][4]) if toks else 0
    rest = compress(data)                                  # tokens for the whole new data
    for t in _tokens(rest):
        if t[0] >= start:
            if t[0] != start:                              # resync: literals up to the next token
                pass
            break
    # re-encode the remainder from `start` with literals until it aligns with a token of `rest`
    new_toks = [t for t in _tokens(rest) if t[0] >= start]
    first = new_toks[0][0] if new_toks else len(data)
    toks += [(k, 'lit', data[k]) for k in range(start, first)]
    toks += new_toks
    out = bytearray(struct.pack('<I', len(data)))
    for g in range(0, len(toks), 8):
        grp = toks[g:g + 8]
        flags = 0; body = bytearray()
        for bit, t in enumerate(grp):
            if t[1] == 'lit':
                flags |= 1 << bit; body.append(t[2])
            else:
                body += bytes((t[2], t[3]))
        out.append(flags); out += body
    assert decompress(bytes(out)) == bytes(data), 'spliced stream does not decode'
    return bytes(out)
