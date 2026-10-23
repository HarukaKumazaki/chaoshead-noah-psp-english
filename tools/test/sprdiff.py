import sys,glob,os; sys.path.insert(0,'tools'); import spriteimg as S, klz, tim2
import numpy as np
from PIL import Image
for n in sys.argv[1:]:
    coz=S.render(os.path.join(S.C0,n+'.webp'),os.path.join(S.C0,n+'_.mvl'))
    coz.save('work/shots/coz_%s.png'%n)
    fs=sorted(glob.glob(os.path.join(S.CHL,n.upper()+'_*.KLZ')))
    print(n, coz.size, len(fs), [os.path.basename(f) for f in fs][:6], flush=True)
    if not fs: continue
    psp,_=tim2.read(klz.decompress(open(fs[0],'rb').read()))
    e,s,dx,dy=S.align(coz,psp); print('  align',round(e,1),round(s,4),dx,dy, flush=True)
    c=coz.resize((round(coz.width*s),round(coz.height*s)),Image.LANCZOS)
    lay=Image.new('RGBA',psp.size,(0,0,0,0)); lay.paste(c,(dx,dy),c)
    a=np.asarray(lay).astype(int); p=np.asarray(psp).astype(int)
    d=(np.abs(a[:,:,:3]-p[:,:,:3]).sum(2)>120)&(a[:,:,3]>250)&(p[:,:,3]>250)
    H,W=d.shape; g=d[:H//20*20,:W//20*20].reshape(H//20,20,W//20,20).mean((1,3))
    for r in g: print('  '+''.join('#' if v>0.25 else '+' if v>0.08 else '.' for v in r))
    comp=Image.new('RGBA',(960,360),(90,90,90,255)); comp.alpha_composite(psp,(0,0)); comp.alpha_composite(lay,(480,0)); comp.save('work/shots/al_%s.png'%n)
