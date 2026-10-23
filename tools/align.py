"""Align PSP script lines to CoZ Steam message segments by Japanese content."""
import sys,os,re,glob,difflib,json,unicodedata
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from pspscr import Script
import msb
SC='unpacked/DATA0/SCENE00.AFS.d'
SEP={0x19,0x08,0x03,0x18}
def segments(raw):
    """split a msb line into display segments; returns list of token lists"""
    segs=[[]]
    for t in msb.tokens(raw):
        segs[-1].append(t)
        if t[0]=='c' and t[1] in SEP: segs.append([])
    if not segs[-1]: segs.pop()
    # drop trailing segments that are only newline/ctrl
    return [s for s in segs if any(t[0]=='g' for t in s)]
def seg_text(seg,strip=True):
    out=[]; ruby=False; name=False
    for t in seg:
        if strip and t[0]=='c' and t[1]==0x01: name=True
        if strip and t[0]=='c' and t[1]==0x02: name=False
        if name: continue
        if t[0]=='c' and t[1]==0x0a: ruby=True
        if t[0]=='c' and t[1]==0x0b: ruby=False
        if t[0]=='g':
            if ruby and strip: continue
            out.append(msb.CH[t[1]] if t[1]<len(msb.CH) else '?')
        elif t[1]==0 and not strip: out.append('\n')
        elif t[1]==1 and not strip: out.append('[')
        elif t[1]==2 and not strip: out.append(']')
    return ''.join(out)
def norm(s):
    s=re.sub(r'^((?:%[A-Z]+\d*)*)【[^】]*】',r'\1',s)   # speaker tag
    s=re.sub(r'%(LC|LE|K|P|N|O\d+|T\d+|[A-Z])','',s)
    s=re.sub(r'\{([^}]*)\}\[[^\]]*\]',r'\1',s)
    s=s.translate(str.maketrans('０１２３４５６７８９','0123456789'))
    s=unicodedata.normalize('NFKC',s)
    full=re.sub(r'[\s【】\[\]]','',s)
    r=re.sub(r'[\s【】\[\]「」『』“”"・、。，．…―ー─!?！？]','',s)
    return r if r else full
    return re.sub(r'[\s【】\[\]「」『』“”"・、。，．…―ー─!?！？]','',s)
def steam_segs(name,lang):
    p=f'steam/mes0{lang}/{name}_0{lang}.msb'
    if not os.path.exists(p): return None
    out=[]
    for i,raw in msb.mes(p):
        for k,s in enumerate(segments(raw)): out.append((i,k,s))
    return out
def dp(A,B,th=0.45):
    """monotone alignment maximizing summed similarity; returns (i,j|None,ratio)"""
    n,m=len(A),len(B)
    R=[[0.0]*m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            sm=difflib.SequenceMatcher(None,A[i],B[j],autojunk=False)
            R[i][j]=sm.ratio() if sm.real_quick_ratio()>=th and sm.quick_ratio()>=th else 0
    S=[[0.0]*(m+1) for _ in range(n+1)]; bk=[[0]*(m+1) for _ in range(n+1)]
    for i in range(1,n+1):
        for j in range(1,m+1):
            best,b=S[i-1][j],1
            if S[i][j-1]>best: best,b=S[i][j-1],2
            r=R[i-1][j-1]
            if r>=th and S[i-1][j-1]+r>best: best,b=S[i-1][j-1]+r,3
            S[i][j]=best; bk[i][j]=b
    i,j=n,m; out={}
    while i>0 and j>0:
        b=bk[i][j]
        if b==3: out[i-1]=(j-1,R[i-1][j-1]); i-=1; j-=1
        elif b==1: i-=1
        else: j-=1
    return [(i,)+out[i] if i in out else (i,None,0) for i in range(n)]
_GLOBAL=None
def global_index():
    """norm(jp segment) -> (file, id, k) over every Steam message file"""
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL={}
        for f in sorted(glob.glob('steam/mes00/*.msb')):
            n=os.path.basename(f)[:-7]
            for i,k,sg in steam_segs(n,0) or []:
                _GLOBAL.setdefault(norm(seg_text(sg)),(n,i,k))
    return _GLOBAL
def global_lookup(t):
    g=global_index()
    if t in g: return g[t]+('global',)
    best=(0,None)
    for k,v in g.items():
        if abs(len(k)-len(t))>max(4,len(t)//4): continue
        sm=difflib.SequenceMatcher(None,t,k,autojunk=False)
        if sm.real_quick_ratio()<0.8 or sm.quick_ratio()<0.8: continue
        r=sm.ratio()
        if r>best[0]: best=(r,v)
    if best[0]>=0.8: return best[1]+('globalfuzzy%.2f'%best[0],)
    return None
def align(name,s):
    jp=steam_segs(name,0); en=steam_segs(name,1)
    if jp is None: return None,None
    enmap={(i,k):sg for i,k,sg in en}
    strs=s.strings()
    seen=set(); psp=[]
    for p,line,so in s.texts:
        if line==0xFFFF or p in seen: continue
        seen.add(p); psp.append((p,line,so,norm(strs[so].decode('cp932','replace'))))
    psp.sort(key=lambda x:x[1])
    A=[x[3] for x in psp]; B=[norm(seg_text(sg)) for _,_,sg in jp]
    sm=difflib.SequenceMatcher(None,A,B,autojunk=False)
    res={}; stats=[0,0,0]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':
            for d in range(i2-i1): res[psp[i1+d][2]]=(jp[j1+d][0],jp[j1+d][1],'exact'); stats[0]+=1
        elif i2>i1:
            for i,j,r in dp(A[i1:i2],B[j1:j2]):
                if j is None: res[psp[i1+i][2]]=None; stats[2]+=1
                else: res[psp[i1+i][2]]=(jp[j1+j][0],jp[j1+j][1],'fuzzy%.2f'%r); stats[1]+=1
    return res,(stats,enmap,jp,psp)
if __name__=='__main__':
    T=[0,0,0]; unm=[]
    for f in sorted(glob.glob(SC+'/*.BIN')):
        n=os.path.basename(f)[:-4].lower()
        s=Script(open(f,'rb').read())
        res,info=align(n,s)
        if res is None: continue
        st=info[0]
        for k in range(3): T[k]+=st[k]
        if st[2]: unm.append((n,st))
    print('exact,fuzzy,unmatched',T)
    for u in unm[:40]: print(u)
