import sys
from PIL import Image
fnt=open(sys.argv[1],'rb').read(); W=H=int(sys.argv[2]); n0=int(sys.argv[3]); cnt=int(sys.argv[4]); out=sys.argv[5]
gs=W*H//2; cols=32; rows=(cnt+cols-1)//cols
img=Image.new('L',(cols*(W+2),rows*(H+2)),40)
for k in range(cnt):
    g=fnt[(n0+k)*gs:(n0+k+1)*gs]
    if len(g)<gs: break
    for y in range(H):
        for x in range(W):
            b=g[(y*W+x)//2]; v=(b>>4) if x%2==0 else (b&0xf)
            img.putpixel(((k%cols)*(W+2)+x,(k//cols)*(H+2)+y),v*17)
img=img.resize((img.width*2,img.height*2),Image.NEAREST); img.save(out)
