import sys,os,struct,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from cpk_extract import utf
f=open(sys.argv[1],'rb'); hdr=f.read(0x800); sz=struct.unpack_from('<I',hdr,8)[0]
cpk=utf(hdr[16:16+sz])[0]
print({k:v for k,v in cpk.items() if not isinstance(v,bytes)})
toc=cpk.get('TocOffset')
if toc:
    f.seek(toc); h=f.read(16); n=struct.unpack_from('<I',h,8)[0]; rows=utf(f.read(n))
    print(len(rows),'files'); c=collections.Counter(os.path.splitext(r['FileName'])[1] for r in rows); print(c)
    for r in rows[:int(sys.argv[2]) if len(sys.argv)>2 else 15]: print(r.get('DirName'),r['FileName'],r['ExtractSize'])
