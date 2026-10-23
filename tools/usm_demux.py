"""Demux a CRI USM: writes the @SFV video elementary stream (and @SFA audio) of channel 0.
Usage: usm_demux.py in.usm outprefix"""
import sys, struct


def demux(path, prefix):
    out = {}
    with open(path, 'rb') as f:
        while True:
            h = f.read(8)
            if len(h) < 8:
                break
            sig = h[:4]; size = struct.unpack('>I', h[4:])[0]
            body = f.read(size)
            if sig in (b'@SFV', b'@SFA'):
                off = body[1]; pad = struct.unpack('>H', body[2:4])[0]; ch = body[4]; typ = body[7] & 3
                if typ == 0 and ch == 0:
                    data = body[off - 8 + 8:size - pad] if False else body[off:size - pad]
                    key = sig[1:4].decode()
                    if key not in out:
                        out[key] = open(prefix + '.' + key.lower(), 'wb')
                    out[key].write(data)
    for v in out.values():
        v.close()
    return list(out)


if __name__ == '__main__':
    print(demux(sys.argv[1], sys.argv[2]))
