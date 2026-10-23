"""Find Japanese text left in every non-script file the build ships (overlay version if present)."""
import os, re, sys, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JP = re.compile(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){3,}')
skip_ext = ('.KLZ', '.klz', '.ahx', '.png', '.PNG', '.P2T', '.p2t', '.ADX', '.AHX', '.FNT', '.FNI', '.PMF', '.AT3', '.json', '.ALS')
res = collections.OrderedDict()
for arch in ('DATA0', 'DATA1'):
    for f in sorted(glob.glob(os.path.join(ROOT, 'unpacked', arch, '*', '*'))):
        if f.endswith(skip_ext) or os.path.basename(f).startswith('_'):
            continue
        rel = os.path.relpath(f, os.path.join(ROOT, 'unpacked'))
        ov = os.path.join(ROOT, 'work', 'ov', rel)
        d = open(ov if os.path.exists(ov) else f, 'rb').read()
        hits = []
        for m in JP.finditer(d):
            try:
                t = m.group().decode('cp932')
            except UnicodeDecodeError:
                continue
            if re.search('[ぁ-んァ-ヶ一-龯]', t):
                hits.append(t)
        if hits:
            res[rel] = hits
for extra in ('work/usrdir/SYSTEM.CFG', 'iso/PSP_GAME/USRDIR/KANDICT.BIN', 'iso/PSP_GAME/USRDIR/CACHELST.TXT'):
    d = open(os.path.join(ROOT, extra), 'rb').read()
    h = [m.group().decode('cp932', 'replace') for m in JP.finditer(d)]
    if h: res[extra] = h
for k, v in res.items():
    print('%-40s %5d  %s' % (k, len(v), ' | '.join(v[:4])[:150]))
