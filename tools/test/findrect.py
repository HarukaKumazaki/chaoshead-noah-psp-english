import struct, glob, collections, os, pickle
p1 = struct.pack('<HH', 204, 448)
c = collections.Counter()
for f in glob.glob('unpacked/DATA0/SCENE00.AFS.d/*.BIN') + ['work/eboot/EBOOT_dec.ELF', 'iso/PSP_GAME/USRDIR/SYSTEM.CFG']:
    d = open(f, 'rb').read()
    i = d.find(p1)
    while i >= 0:
        n = os.path.basename(f)
        c[n] += 1
        if c[n] <= 2:
            print(n, hex(i), d[i - 12:i + 12].hex())
        i = d.find(p1, i + 1)
print(c.most_common(5))
ins = pickle.load(open('work/dis.pkl', 'rb'))
for k, (a, m, o) in enumerate(ins):
    if o.endswith(', 0xcc') and m in ('addiu', 'ori'):
        w = ' '.join(oo for _, _, oo in ins[k - 8:k + 10])
        if '0x1c0' in w or ', 0x3c' in w:
            print(hex(a), ' ; '.join(mm + ' ' + oo for _, mm, oo in ins[k - 4:k + 8]))
