r"""CoZ song subtitles -> [(japanese line, english line)] per .ass file.
Kanji lines are rebuilt from the per-character karaoke fx events (static \fad(300,250) layer,
grouped by start/end, ordered by position); the English is the 'trad' line overlapping in time."""
import os, re, glob

SUBS = r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\subs'


def _t(s):
    h, m, x = s.split(':'); return int(h) * 3600 + int(m) * 60 + float(x)


def pairs(name):
    kan, tr = {}, []
    for ln in open(os.path.join(SUBS, name), encoding='utf-8-sig'):
        if not ln.startswith(('Dialogue:', 'Comment:')):
            continue
        p = ln.rstrip('\n').split(',', 9)
        st, a, b, txt = p[3], _t(p[1]), _t(p[2]), p[9]
        if 'furigana' in st or 'Copy' in st:
            continue
        if ln.startswith('Dialogue:') and 'kanji' in st and r'\fad(300,250)' in txt:
            m = re.search(r'\\pos\(([\d.]+),([\d.]+)\)', txt)
            ch = re.sub(r'\{[^}]*\}', '', txt)
            if m:
                kan.setdefault((a, b), []).append((float(m.group(1)), float(m.group(2)), ch))
        elif ln.startswith('Dialogue:') and 'trad' in st:
            t = re.sub(r'\{[^}]*\}', '', txt).replace(r'\N', ' ').strip()
            if t:
                tr.append((a, b, t))
    out = []
    for (a, b), chars in sorted(kan.items()):
        xs = {round(c[0]) for c in chars}
        vertical = len(xs) == 1
        chars.sort(key=lambda c: (c[1], c[0]) if vertical else (c[0], c[1]))
        jp = ''.join(c[2] for c in chars)
        best = max(tr, key=lambda t: min(b, t[1]) - max(a, t[0]), default=None)
        if best and min(b, best[1]) - max(a, best[0]) > 0.5:
            out.append((jp, best[2]))
    return out


def all_pairs():
    res = {}
    for f in glob.glob(os.path.join(SUBS, '*.ass')):
        n = os.path.basename(f)
        if 'karaonly' in n or 'tlonly' in n:
            continue
        res[n] = pairs(n)
    return res


if __name__ == '__main__':
    import sys
    for jp, en in pairs(sys.argv[1]):
        print(jp, '=>', en)
