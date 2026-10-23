"""Minimal CRI CPK extractor (UTF tables + CRILAYLA). Usage: cpk_extract.py in.cpk outdir"""
import struct,sys,os
def decrypt_utf(buf):
    out=bytearray(len(buf)); m=0x655f
    for i,c in enumerate(buf):
        out[i]=c^(m&0xff); m=(m*0x4115)&0xffffffff
    return bytes(out)
def utf(buf):
    if buf[:4]!=b'@UTF': buf=decrypt_utf(buf)
    assert buf[:4]==b'@UTF',buf[:4]
    size,rows_off,str_off,data_off,name_off,ncol,rowlen,nrows=struct.unpack_from('>IIIIIHHI',buf,4)
    b=8; rows_off+=b; str_off+=b; data_off+=b
    def s(o): e=buf.index(b'\0',str_off+o); return buf[str_off+o:e].decode('utf-8','replace')
    def rd(t,p):
        if t in(0,1): v=struct.unpack_from('>B' if t==0 else '>b',buf,p)[0]; return v,1
        if t in(2,3): return struct.unpack_from('>H' if t==2 else '>h',buf,p)[0],2
        if t in(4,5): return struct.unpack_from('>I' if t==4 else '>i',buf,p)[0],4
        if t in(6,7): return struct.unpack_from('>Q' if t==6 else '>q',buf,p)[0],8
        if t==8: return struct.unpack_from('>f',buf,p)[0],4
        if t==0xA: return s(struct.unpack_from('>I',buf,p)[0]),4
        if t==0xB: o,l=struct.unpack_from('>II',buf,p); return buf[data_off+o:data_off+o+l],8
        raise ValueError(t)
    cols=[];p=b+24
    for i in range(ncol):
        fl=buf[p]; nm=s(struct.unpack_from('>I',buf,p+1)[0]); p+=5
        const=None
        if fl&0xf0==0x30: const,l=rd(fl&0xf,p); p+=l
        cols.append((fl,nm,const))
    out=[]
    for r in range(nrows):
        p=rows_off+r*rowlen; row={}
        for fl,nm,const in cols:
            st=fl&0xf0
            if st==0x50: v,l=rd(fl&0xf,p); p+=l; row[nm]=v
            elif st==0x30: row[nm]=const
            else: row[nm]=None
        out.append(row)
    return out
def crilayla(d):
    usize,hoff=struct.unpack_from('<II',d,8)
    prefix=d[16+hoff:16+hoff+0x100]
    res=bytearray(usize+0x100); res[:0x100]=prefix
    src=d; pos=len(src)-0x100-1; bits=0; nbits=0
    def get(n):
        nonlocal pos,bits,nbits
        v=0
        while n:
            if nbits==0:
                bits=src[pos]; pos-=1; nbits=8
            take=min(n,nbits)
            v=(v<<take)|((bits>>(nbits-take))&((1<<take)-1))
            nbits-=take; n-=take
        return v
    out=usize+0x100-1; end=0x100
    while out>=end:
        if get(1):
            off=out+get(13)+3
            ln=3; lv=[2,3,5,8]; i=0
            while True:
                v=get(lv[min(i,3)]); ln+=v
                if v!=(1<<lv[min(i,3)])-1: break
                i+=1
            for _ in range(ln):
                res[out]=res[off]; out-=1; off-=1
                if out<end: break
        else:
            res[out]=get(8); out-=1
    return bytes(res)
def main(path,outdir):
    f=open(path,'rb'); hdr=f.read(0x800)
    assert hdr[:4]==b'CPK '
    sz=struct.unpack_from('<I',hdr,8)[0]
    cpk=utf(hdr[16:16+sz])[0]
    toc=cpk.get('TocOffset'); itoc=cpk.get('ItocOffset')
    content=cpk.get('ContentOffset')
    files=[]
    if toc:
        f.seek(toc); h=f.read(16); n=struct.unpack_from('<I',h,8)[0]
        rows=utf(f.read(n))
        base=min(toc,content) if content else toc
        for r in rows:
            name=(r['DirName']+'/' if r.get('DirName') else '')+r['FileName']
            files.append((r.get('ID'),name,base+r['FileOffset'],r['FileSize'],r['ExtractSize']))
    else:
        # ITOC-only: files are stored in ID order from ContentOffset, each aligned to 'Align'
        f.seek(itoc); h=f.read(16); n=struct.unpack_from('<I',h,8)[0]
        it=utf(f.read(n))[0]
        sizes={}
        for key in ('DataL','DataH'):
            if it.get(key):
                for r in utf(it[key]):
                    sizes[r['ID']]=(r['FileSize'],r.get('ExtractSize') or r['FileSize'])
        align=cpk.get('Align') or 2048
        off=content
        for i in sorted(sizes):
            fs,es=sizes[i]
            files.append((i,'%05d.bin'%i,off,fs,es))
            off+=fs
            off=(off+align-1)//align*align
    os.makedirs(outdir,exist_ok=True)
    for i,name,off,fs,es in files:
        f.seek(off); d=f.read(fs)
        if d[:8]==b'CRILAYLA': d=crilayla(d)
        op=os.path.join(outdir,*name.split('/')); os.makedirs(os.path.dirname(op) or outdir,exist_ok=True)
        open(op,'wb').write(d)
    print(path,len(files),'files')
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
