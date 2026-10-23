import sys,time; sys.path.insert(0,'tools'); import ppdbg
import numpy as np
from PIL import Image
ROWS=[.163,.241,.323,.404]
def sel():
    ws=ppdbg.connect(); ppdbg.shot(ws,'work/shots/ms.png'); ws.close()
    im=np.asarray(Image.open('work/shots/ms.png').convert('L')).astype(float); H,W=im.shape
    v=[im[int(r*H)-10:int(r*H)+10,int(.165*W):int(.185*W)].max() for r in ROWS]
    return int(np.argmax(v)), [round(x) for x in v]
def goto(target):
    for _ in range(12):
        s,v=sel(); print('at',s,v,flush=True)
        if s==target: return True
        ws=ppdbg.connect(); ppdbg.press(ws,'down',1,600,200); ws.close(); time.sleep(0.8)
    return False
if __name__=='__main__':
    print(goto(int(sys.argv[1])))
