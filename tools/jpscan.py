"""Report referenced script strings that still contain real Japanese (custom 0x85/0x86 glyphs ignored)."""
import sys, glob, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pspscr import Script


def real_jp(raw):
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            if c not in (0x85, 0x86):
                out.append(raw[i:i + 2].decode('cp932', 'replace'))
            i += 2
        else:
            i += 1
    t = ''.join(out)
    return re.sub('[【】“”‘’…―－！？、。・～♪∬]', '', t)


if __name__ == '__main__':
    left = collections.Counter()
    for f in glob.glob(os.path.join(sys.argv[1], '*.BIN')):
        s = Script(open(f, 'rb').read())
        used = set(v for q, v in s.refs) | set(so for p, l, so in s.texts)
        for o, raw in s.strings().items():
            if o in used:
                body = re.sub(rb'\x81\x79.*?\x81\x7a', b'', raw)   # speaker keys 【..】 stay Japanese
                jp = real_jp(body)
                if re.search('[぀-ヿ一-鿿]', jp):
                    left[(os.path.basename(f), raw.decode('cp932', 'replace')[:60])] += 1
    print('strings with Japanese:', len(left))
    for k in list(left)[:30]:
        print(k)
