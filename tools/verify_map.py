import sys,os,re,glob
sys.path.insert(0,os.path.dirname(__file__))
from pspscr import Script
import msb
SC='unpacked/DATA0/SCENE00.AFS.d'
def norm_psp(s):
    s=re.sub(r'%(LC|LE|K|P|N|O\d+|T\d+|[A-Z])','',s)
    s=re.sub(r'\{([^}]*)\}\[[^\]]*\]',r'\1',s)
    s=s.replace('【','').replace('】','')
    return re.sub(r'\s','',s)
def norm_mes(s):
    s=re.sub(r'\{[0-9a-f]+\}','',s).replace('[','').replace(']','')
    return re.sub(r'\s','',s)
tot=ok=miss=0; bad=[]; rt=0
for f in sorted(glob.glob(SC+'/*.BIN')):
    n=os.path.basename(f)[:-4].lower()
    data=open(f,'rb').read()
    s=Script(data)
    if s.rebuild({})[:len(data)].rstrip(b'\0')!=data.rstrip(b'\0'): rt+=1; print('ROUNDTRIP FAIL',n)
    mp=f'steam/mes00/{n}_00.msb'
    if not os.path.exists(mp): 
        if s.texts: print('no msb for',n,len(s.texts))
        continue
    jp={i:msb.dec(r,False) for i,r in msb.mes(mp)}
    strs=s.strings()
    for p,line,so in s.texts:
        if line==0xFFFF: continue
        tot+=1
        a=norm_psp(strs[so].decode('cp932','replace')); m=jp.get(line*100)
        if m is None: miss+=1; bad.append((n,line,a,None)); continue
        if a==norm_mes(m): ok+=1
        else: bad.append((n,line,a,norm_mes(m)))
print('total',tot,'exact',ok,'missing',miss,'diff',len(bad)-miss,'roundtrip fails',rt)
import difflib
for x in bad[:25]: print(x)
r=[difflib.SequenceMatcher(None,a,m).ratio() for n,l,a,m in bad if m]
print('diffs with ratio<0.6:',sum(1 for x in r if x<0.6))
