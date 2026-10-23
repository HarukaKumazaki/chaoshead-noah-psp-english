"""Audit the injected script text (work/report.tsv) for likely misalignments.

Flags
  dup      the same English on two consecutive different Japanese lines
  ratio    English length implausible for the Japanese length
  quote    dialogue (「」) in one language but narration in the other
  tips     TIPS keyword code count differs (%BnS)
  empty    Japanese text with no English
Usage: audit.py [report.tsv] > audit.txt
"""
import sys, re, collections

CODE = re.compile(r'%(?:[NKP]|LC|LE|O\d{3}|T\d{3}|S\d{3}|t\d{3}|FS|FE|B\dS|B\dE|n|p)|【[^】]*】|∬|\{[^}]*\}\[[^\]]*\]')


def plain(t):
    return CODE.sub('', t).replace('　', ' ').strip()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'work/report.tsv'
    rows = [ln.rstrip('\n').split('\t') for ln in open(path, encoding='utf-8')]
    rows = [r + [''] * (5 - len(r)) for r in rows]
    flags = collections.Counter()
    out = []
    prev = None
    for name, line, how, jp, en in rows:
        if line == '-1':
            continue
        pj, pe = plain(jp), plain(en)
        f = []
        if pj and not pe:
            f.append('empty')
        if pj and pe:
            r = len(pe) / max(1, len(pj))
            if (len(pj) >= 12 and r < 0.6) or (len(pj) >= 4 and r > 9):
                f.append('ratio%.1f' % r)
            jq = '「' in jp or '『' in jp[:3]
            eq = '“' in en or '"' in en
            if '【' in jp and jq != eq:
                f.append('quote')
        if len(re.findall(r'%B\dS', jp)) != len(re.findall(r'%B\dS', en)):
            f.append('tips')
        if prev and prev[0] == name and pe and len(pe) > 15 and pe == prev[2] and pj != prev[1]:
            f.append('dup')
        for x in f:
            flags[re.sub(r'[\d.]+$', '', x)] += 1
        if f:
            out.append('%s\t%s\t%s\t%s\t%s\t%s' % (name, line, ','.join(f), how, jp, en))
        prev = (name, pj, pe)
    print('# flags:', dict(flags), file=sys.stderr)
    print('\n'.join(out))


if __name__ == '__main__':
    main()
