"""advance with circle until a NEW Tips highlight line is fully shown; save work/shots/z.png"""
import sys, time; sys.path.insert(0, 'tools'); import ppdbg
from PIL import Image
import numpy as np
ws = ppdbg.connect()
def cyan():
    ppdbg.shot(ws, 'work/shots/z.png')
    a = np.asarray(Image.open('work/shots/z.png').convert('RGB')).astype(int)
    box = a[int(a.shape[0] * 0.66):, 40:-40]
    return ((box[:, :, 0] < 130) & (box[:, :, 1] > 170) & (box[:, :, 2] > 170) & (box[:, :, 2] - box[:, :, 0] > 80)).sum()
prev = cyan() > 150
for k in range(int(sys.argv[1]) if len(sys.argv) > 1 else 80):
    ppdbg.press(ws, 'circle', 1, 700, 100); time.sleep(0.5)
    now = cyan() > 150
    if now and not prev:
        time.sleep(3); cyan(); print('highlight after', k + 1, 'presses'); break
    prev = now
else:
    print('none')
