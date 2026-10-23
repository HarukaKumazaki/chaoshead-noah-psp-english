"""Export every picture in the game (final English version where one exists) to work/audit/img/*.png
with an index work/audit/index.tsv: name, source, replaced(0/1), w, h"""
import sys, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import klz, tim2, p2t
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'work', 'audit', 'img'); os.makedirs(OUT, exist_ok=True)
rows = []
for arch in ('DATA0', 'DATA1'):
    for d in sorted(glob.glob(os.path.join(ROOT, 'unpacked', arch, '*.AFS.d'))):
        sub = os.path.basename(d)
        for f in sorted(os.listdir(d)):
            ext = f.rsplit('.', 1)[-1].upper()
            ovp = os.path.join(ROOT, 'work', 'ov', arch, sub, f)
            src = ovp if os.path.exists(ovp) else os.path.join(d, f)
            rep = int(src == ovp)
            try:
                if ext.startswith('KLZ'):
                    raw = klz.decompress(open(src, 'rb').read())
                    if raw[:4] != b'TIM2':
                        continue
                    im, info = tim2.read(raw)
                    name = '%s_%s_%s' % (arch, sub[:-6], f.replace('#', '_'))
                    im.save(os.path.join(OUT, name + '.png')); rows.append((name, src, rep, im.width, im.height))
                elif ext == 'P2T':
                    b = open(src, 'rb').read()
                    for i, e in enumerate(p2t.entries(b)):
                        im, info = p2t.image(b, e)
                        name = '%s_%s_%s_%d' % (arch, sub[:-6], f, i)
                        im.save(os.path.join(OUT, name + '.png')); rows.append((name, src, rep, im.width, im.height))
                elif ext == 'PNG':
                    im = Image.open(src); name = '%s_%s_%s' % (arch, sub[:-6], f)
                    im.save(os.path.join(OUT, name + '.png')); rows.append((name, src, rep, im.width, im.height))
            except Exception as ex:
                print('skip', f, ex)
for f in ('ICON0.PNG', 'PIC1.PNG'):
    p = os.path.join(ROOT, 'work', 'psp_game', f)
    src = p if os.path.exists(p) else os.path.join(ROOT, 'iso', 'PSP_GAME', f)
    im = Image.open(src); im.save(os.path.join(OUT, 'PSP_GAME_' + f)); rows.append(('PSP_GAME_' + f[:-4], src, int(src == p), im.width, im.height))
with open(os.path.join(ROOT, 'work', 'audit', 'index.tsv'), 'w', encoding='utf-8') as o:
    for r in rows:
        o.write('\t'.join(map(str, r)) + '\n')
print('exported', len(rows), 'pictures; replaced', sum(r[2] for r in rows))
