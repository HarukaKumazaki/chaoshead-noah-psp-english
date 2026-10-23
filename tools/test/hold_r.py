"""hold R (force skip) for N seconds, screenshot every few seconds: python tools/test/hold_r.py 90 10 tag"""
import sys, time; sys.path.insert(0, 'tools'); import ppdbg
ws = ppdbg.connect()
dur, step, tag = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
ppdbg.call(ws, 'input.buttons.send', buttons={'rtrigger': True})
t0 = time.time(); k = 0
try:
    while time.time() - t0 < dur:
        time.sleep(step)
        ppdbg.shot(ws, 'work/shots/%s_%02d.png' % (tag, k)); k += 1
        st = ppdbg.call(ws, 'cpu.status')
        print('%5.1fs pc %08x' % (time.time() - t0, st['pc']), flush=True)
finally:
    ppdbg.call(ws, 'input.buttons.send', buttons={'rtrigger': False})
