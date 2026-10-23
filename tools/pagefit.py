"""Rows per text page after injection: English pages that may not fit the message box.
A page = strings up to one ending in %P. Pages whose Japanese fits the small box (<= 3 rows of
~25 full-width characters) are treated as bottom-box pages (capacity BOX_ROWS)."""
import sys, re, collections
BOX_ROWS = 5
CODE = re.compile(r'%(?:K|LC|LE|O\d{3}|T\d{3}|S\d{3}|t\d{3}|FS|FE|B\d[SE]|n|p)|【[^】]*】|∬')


def jprows(t):
    t = CODE.sub('', t).replace('%N', '').replace('%P', '')
    w = sum(8 if ord(c) < 0x100 else (11 if c in '、。，．・「」『』（）！？…―ー' else 17) for c in t)
    return -(-w // 432) if t.strip() else 0


def en_rows(strings):
    rows, open_ = 0, False
    for s in strings:
        segs = s.replace('%P', '').split('%N')
        for k, seg in enumerate(segs):
            vis = CODE.sub('', seg)
            if k > 0:
                open_ = False
            if vis.strip():
                if not open_:
                    rows += 1; open_ = True
        if s.rstrip().endswith('%N'):
            open_ = False
    return rows


def main(rep='work/report.tsv'):
    sc = collections.OrderedDict()
    for ln in open(rep, encoding='utf-8'):
        r = ln.rstrip('\n').split('\t')
        if len(r) < 5 or r[1] == '-1':
            continue
        sc.setdefault(r[0], []).append((int(r[1]), r[3], r[4]))
    bad, dist = [], collections.Counter()
    for name, items in sc.items():
        items.sort(); pj, pe, nos = [], [], []
        for no, jp, en in items:
            pj.append(jp); pe.append(en); nos.append(no)
            if '%P' in jp:
                J = sum(jprows(x) for x in pj); E = en_rows(pe)
                if J <= 3:
                    dist[E] += 1
                    if E > BOX_ROWS:
                        bad.append((name, nos, E))
                pj, pe, nos = [], [], []
    print('box pages by rows:', sorted(dist.items()), '| over', BOX_ROWS, ':', len(bad))
    return bad


if __name__ == '__main__':
    for b in main(*(sys.argv[1:2] or []))[:30]:
        print(b)
