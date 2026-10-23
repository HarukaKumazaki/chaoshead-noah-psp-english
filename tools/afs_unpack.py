"""Recursive AFS unpacker. Usage: afs_unpack.py in.afs outdir"""
import struct,sys,os,json
def read_afs(buf):
    assert buf[:4]==b'AFS\0'
    n=struct.unpack_from('<I',buf,4)[0]
    ent=[struct.unpack_from('<II',buf,8+8*i) for i in range(n)]
    noff,nsz=struct.unpack_from('<II',buf,8+8*n)
    names=[];meta=[]
    for i in range(n):
        if noff:
            r=buf[noff+48*i:noff+48*i+48]; names.append(r[:32].split(b'\0')[0].decode('ascii')); meta.append(r[32:48].hex())
        else: names.append('%05d.bin'%i); meta.append(None)
    return ent,names,meta,(noff!=0)
def unpack(buf,out):
    ent,names,meta,hasnames=read_afs(buf)
    os.makedirs(out,exist_ok=True)
    man={'hasnames':hasnames,'files':[]}
    used=set()
    for i,((o,sz),nm,m) in enumerate(zip(ent,names,meta)):
        data=buf[o:o+sz]
        item={'name':nm,'meta':m}
        fn=nm
        if fn.upper() in used: fn='%s#%05d'%(nm,i); item['file']=fn  # duplicate names exist
        used.add(fn.upper())
        if data[:4]==b'AFS\0':
            unpack(data,os.path.join(out,fn+'.d')); item['afs']=True
        else:
            open(os.path.join(out,fn),'wb').write(data)
        man['files'].append(item)
    json.dump(man,open(os.path.join(out,'_manifest.json'),'w'),indent=0)
unpack(open(sys.argv[1],'rb').read(),sys.argv[2])
