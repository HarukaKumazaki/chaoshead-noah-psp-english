"""PSP .PMF (PSMF) remuxer: new H.264 video + the original ATRAC3plus audio packs.

Layout reproduced from the retail files:
- 0x800 PSMF header (only the stream size at 0x0C changes; frame count must stay the same)
- 2048-byte MPEG-PS packs; every GOP starts a pack with the system header (0xBB), a 0xBF GOP
  index and a video PES carrying PTS/DTS + P-STD extension; a GOP's last pack is padded (0xBE)
- 0xBF index: 01 e0, u16 x4 = pack (relative to the GOP's first pack) holding the end of
  pictures 1..4, 4 zero bytes, u16 4n+2, u16 n, n x (00 80 size_hi size_lo) picture sizes
- audio packs are copied whole from the original, interleaved ~0.3 s ahead of the video
Video PTS = DTS + 3003, first DTS taken from the original.

Usage: pmf.py orig.PMF new.h264 out.PMF
"""
import struct, sys

PACK = 0x800
FRAME = 3003


def _ts(b):
    return ((b[0] >> 1) & 7) << 30 | b[1] << 22 | (b[2] >> 1) << 15 | b[3] << 7 | b[4] >> 1


def _put_ts(prefix, t):
    return bytes([prefix << 4 | ((t >> 30) & 7) << 1 | 1, (t >> 22) & 0xff, ((t >> 15) & 0x7f) << 1 | 1,
                  (t >> 7) & 0xff, (t & 0x7f) << 1 | 1])


def _scr_bytes(scr):
    b = bytearray(6)
    b[0] = 0x40 | ((scr >> 30) & 7) << 3 | 0x04 | ((scr >> 28) & 3)
    b[1] = (scr >> 20) & 0xff
    b[2] = ((scr >> 15) & 0x1f) << 3 | 0x04 | ((scr >> 13) & 3)
    b[3] = (scr >> 5) & 0xff
    b[4] = (scr & 0x1f) << 3 | 0x04
    b[5] = 0x01                                   # scr extension 0 + marker
    return bytes(b)


def read_orig(path):
    b = open(path, 'rb').read()
    o = dict(header=b[:PACK], audio=[], sysh=None, mux=None, dts0=None, pts0=None)
    for i in range(PACK, len(b), PACK):
        p = b[i:i + PACK]
        if o['mux'] is None:
            o['mux'] = p[10:14]
        j = 14 + (p[13] & 7)
        first = None
        while j < PACK and p[j:j + 3] == b'\0\0\1':
            sid = p[j + 3]; L = struct.unpack('>H', p[j + 4:j + 6])[0]
            if first is None:
                first = sid
            if sid == 0xbb and o['sysh'] is None:
                o['sysh'] = p[j:j + 6 + L]
            if sid == 0xe0 and o['dts0'] is None and p[j + 7] & 0x40:
                o['pts0'] = _ts(p[j + 9:j + 14]); o['dts0'] = _ts(p[j + 14:j + 19])
            if sid == 0xbd and first == 0xbd and j == 14 + (p[13] & 7):
                pts = _ts(p[j + 9:j + 14]) if p[j + 7] & 0x80 else None
                o['audio'].append([pts, bytearray(p)])
            j += 6 + L
    last = None                    # audio packs without PTS inherit the previous one
    for a in o['audio']:
        if a[0] is None:
            a[0] = last
        last = a[0]
    return o


def access_units(es):
    """split Annex-B ES at access unit delimiters -> [(bytes, is_idr)]"""
    starts = []
    i = es.find(b'\0\0\1\x09')
    while i >= 0:
        s = i - 1 if i > 0 and es[i - 1] == 0 else i
        starts.append(s)
        i = es.find(b'\0\0\1\x09', i + 4)
    aus = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(es)
        au = es[s:e]
        idr = False
        j = au.find(b'\0\0\1')
        while j >= 0:
            if au[j + 3] & 0x1f == 5:
                idr = True; break
            j = au.find(b'\0\0\1', j + 3)
        aus.append((au, idr))
    return aus


def mux(orig, es, nframes=None):
    aus = access_units(es)
    if nframes is not None:
        assert len(aus) >= nframes, (len(aus), nframes)
        aus = aus[:nframes]
    gops = []
    for k, (au, idr) in enumerate(aus):
        if idr or not gops:
            gops.append([])
        gops[-1].append(k)
    dts0 = orig['dts0']
    audio = list(orig['audio'])
    LEAD = 27000
    packs = []                     # [kind, bytearray(2048), ref_ts or None]

    def pack_header():
        return bytearray(b'\0\0\1\xba' + bytes(6) + orig['mux'] + b'')[:14]

    def emit_audio_until(dts):
        while audio and audio[0][0] is not None and audio[0][0] <= dts + LEAD:
            pts, p = audio.pop(0)
            packs.append(['a', bytearray(p), pts])

    for g in gops:
        n = len(g)
        bf = b'\x01\xe0' + bytes(8) + bytes(4) + struct.pack('>HH', 4 * n + 2, n)
        for k in g:
            sz = len(aus[k][0])
            assert sz < 0x10000, 'picture too large for the GOP index: %d' % sz
            bf += b'\x00\x80' + struct.pack('>H', sz)
        gop_first = len(packs)
        data = b''.join(aus[k][0] for k in g)
        bounds = []                # (start offset in data, au index)
        off = 0
        for k in g:
            bounds.append((off, k)); off += len(aus[k][0])
        ends = [b0 + len(aus[k][0]) - 1 for b0, k in bounds]
        pos = 0
        first_pack = True
        pic_pack = {}
        while pos < len(data):
            cur_k = max(k for b0, k in bounds if b0 <= pos)
            if not first_pack:                   # the GOP's index pack comes first
                emit_audio_until(dts0 + cur_k * FRAME)
            p = pack_header()
            if first_pack:
                p += orig['sysh']
                p += b'\0\0\1\xbf' + struct.pack('>H', len(bf)) + bf
                bf_at = len(p) - len(bf)
            room = PACK - len(p) - 6 - 3
            # PTS/DTS of the first AU starting inside this payload
            starting = [(b0, k) for b0, k in bounds if b0 >= pos]
            hdr_ext = b''
            flags2 = 0
            if first_pack:
                k0 = g[0]
                hdr_ext = _put_ts(3, dts0 + FRAME + k0 * FRAME) + _put_ts(1, dts0 + k0 * FRAME) + b'\x1e\x60\xfb'
                flags2 = 0xc1
            elif starting and starting[0][0] < pos + room - 10:
                k0 = starting[0][1]
                hdr_ext = _put_ts(3, dts0 + FRAME + k0 * FRAME) + _put_ts(1, dts0 + k0 * FRAME)
                flags2 = 0xc0
            room -= len(hdr_ext)
            chunk = data[pos:pos + room]
            gap = room - len(chunk)
            if 0 < gap < 6:                      # leave room for a padding packet
                chunk = chunk[:len(chunk) - (6 - gap)]
            pes = b'\0\0\1\xe0' + struct.pack('>H', 3 + len(hdr_ext) + len(chunk)) + \
                bytes([0x81, flags2, len(hdr_ext)]) + hdr_ext + chunk
            p += pes
            left = PACK - len(p)
            if left:
                if left < 6:       # too small for a padding packet: stuff the video PES header instead
                    raise RuntimeError('padding gap %d' % left)
                p += b'\0\0\1\xbe' + struct.pack('>H', left - 6) + b'\xff' * (left - 6)
            ref = dts0 + cur_k * FRAME
            packs.append(['v', p, ref])
            if first_pack:
                gop_first = len(packs) - 1
            idx = len(packs) - 1 - gop_first
            for e, k in zip(ends, g):
                if pos <= e < pos + len(chunk):
                    pic_pack[k] = idx
            pos += len(chunk)
            if first_pack:
                gop_pack = packs[-1]
            first_pack = False
        vals = [pic_pack[g[min(i, n - 1)]] for i in range(4)]
        struct.pack_into('>HHHH', gop_pack[1], bf_at + 2, *vals)
    emit_audio_until(1 << 40)
    # system clock: monotonic, ahead of every timestamp in the pack
    scr = None
    out = bytearray(orig['header'])
    for kind, p, ref in packs:
        want = max(0, ref - 30000)
        scr = want if scr is None else max(scr + 148, want)
        p[4:10] = _scr_bytes(scr)
        out += p
    struct.pack_into('>I', out, 0x0C, len(out) - PACK)
    return bytes(out)


if __name__ == '__main__':
    o = read_orig(sys.argv[1])
    open(sys.argv[3], 'wb').write(mux(o, open(sys.argv[2], 'rb').read()))
