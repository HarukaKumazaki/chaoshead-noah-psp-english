"""Exact 480x272 framebuffer capture through the PPSSPP debugger (pauses for a moment)."""
import sys, os, base64, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppdbg


def fbshot(ws, out):
    ppdbg.call(ws, 'cpu.stepping'); time.sleep(0.2)
    try:
        r = ppdbg.call(ws, 'gpu.buffer.screenshot', type='base64', alpha=False)
        data = r.get('base64') or r.get('uri', '').split(',', 1)[-1]
        open(out, 'wb').write(base64.b64decode(data))
    finally:
        ppdbg.call(ws, 'cpu.resume')
    return out


if __name__ == '__main__':
    print(fbshot(ppdbg.connect(), sys.argv[1]))
