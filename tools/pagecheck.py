"""Rows per text page: Japanese vs English, per scene (window capacity = max rows the Japanese used)."""
import sys, re, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc

CODE = re.compile(r'%(?:K|LC|LE|O\d{3}|T\d{3}|S\d{3}|t\d{3}|FS|FE|B\d[SE]|n|p)|【[^】]*】|∬|\{([^}]*)\}\[[^\]]*\]')


def jp_rows(seg):
    t = CODE.sub(lambda m: m.group(1) or '', seg)
    w = sum(8 if ord(c) < 0x100 else (11 if c in '、。，．・「」『』（）！？…―ー' else 17) for c in t)
    return max(1, -(-w // 432)) if t.strip() else 1


def pages(strings, en):
    """yield (rows, [string indices]) per page; %N = newline, %P = new page"""
    rows, idx, col_open = 0, [], False
    for i, s in enumerate(strings):
        parts = re.split(r'(%N|%P)', s)
        for p in parts:
            if p == '%N':
                rows += 0 if not col_open else 0; col_open = False
                continue
            if p == '%P':
                if idx or rows:
                    yield rows, idx + [i]
                rows, idx, col_open = 0, [], False
                continue
            t = CODE.sub(lambda m: m.group(1) or '', p)
            if not t:
                continue
            if en:
                n = 1 if col_open else 1
                rows += (0 if col_open else 1)
            else:
                k = jp_rows(p)
                rows += (k - 1) if col_open else k
            col_open = True
        idx.append(i)
    if idx:
        yield rows, idx


def main():
    rep = sys.argv[1] if len(sys.argv) > 1 else 'work/report.tsv'
    sc = collections.OrderedDict()
    for ln in open(rep, encoding='utf-8'):
        r = ln.rstrip('\n').split('\t')
        if len(r) < 5 or r[1] == '-1':
            continue
        sc.setdefault(r[0], []).append((int(r[1]), r[3], r[4]))
    over = []
    for name, items in sc.items():
        items.sort()
        jp = [x[1] for x in items]; en = [x[2] for x in items]
        jpmax = max((r for r, _ in pages(jp, False)), default=0)
        for r, idx in pages(en, True):
            if r > jpmax:
                over.append((name, jpmax, r, [items[i][0] for i in idx]))
    caps = collections.Counter()
    for name, items in sc.items():
        caps[max((r for r, _ in pages([x[1] for x in sorted(items)], False)), default=0)] += 1
    print('scene window capacities (max JP rows/page):', sorted(caps.items()))
    print('English pages over capacity:', len(over))
    for o in over[:15]:
        print('  ', o)
    return over


if __name__ == '__main__':
    main()
