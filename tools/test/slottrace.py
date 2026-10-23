"""Trace glyph-slot renders (0x88e5e34 slot, str): python work/slottrace.py N [buttons...]
Adds a CPU breakpoint, presses the buttons, then logs N hits as slot / ra / text."""
import sys, json, time, base64
sys.path.insert(0, 'tools'); import ppdbg

ws = ppdbg.connect()
n = int(sys.argv[1])
ppdbg.call(ws, 'cpu.breakpoint.add', address=0x088e5e34)
for b in sys.argv[2:]:
    ppdbg.call(ws, 'input.buttons.send', buttons={b: True}); time.sleep(0.15)
    ppdbg.call(ws, 'input.buttons.send', buttons={b: False}); time.sleep(0.3)


def reg(name):
    return int(ppdbg.call(ws, 'cpu.getReg', name=name)['uintValue'])


def text(addr):
    raw = base64.b64decode(ppdbg.call(ws, 'memory.read', address=addr, size=96)['base64'])
    raw = raw.split(b'\0')[0]
    return raw.decode('cp932', 'replace')


hits = 0
try:
    while hits < n:
        st = ppdbg.call(ws, 'cpu.status')
        if not st.get('stepping'):
            time.sleep(0.05); continue
        a0, a1, ra = reg('a0'), reg('a1'), reg('ra')
        print('slot %4d  ra %08x  %r' % (a0, ra, text(a1)), flush=True)
        hits += 1
        ppdbg.call(ws, 'cpu.resume')
        time.sleep(0.02)
finally:
    ppdbg.call(ws, 'cpu.breakpoint.remove', address=0x088e5e34)
    if ppdbg.call(ws, 'cpu.status').get('stepping'):
        ppdbg.call(ws, 'cpu.resume')
