"""press circle quickly; every 8 presses check the text box for a Tips highlight (cyan); stop there"""
import sys, time; sys.path.insert(0, 'tools'); import ppdbg
from PIL import Image
import numpy as np
ws = ppdbg.connect()
def cyan():
    ppdbg.shot(ws, 'work/shots/z.png')
    a = np.asarray(Image.open('work/shots/z.png').convert('RGB')).astype(int)
    box = a[int(a.shape[0] * 0.66):, 40:-40]
    if box.mean() > 110:              # no dark message box (movie, white screen)
        return 0
    return ((box[:, :, 0] < 130) & (box[:, :, 1] > 170) & (box[:, :, 2] > 170) & (box[:, :, 2] - box[:, :, 0] > 80)).sum()
for k in range(int(sys.argv[1])):
    ppdbg.press(ws, 'circle', 8, 250, 90)
    if cyan() > 150:
        time.sleep(3); cyan(); print('highlight after', (k + 1) * 8, 'presses'); break
else:
    print('none')
