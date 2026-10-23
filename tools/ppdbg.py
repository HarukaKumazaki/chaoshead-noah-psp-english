"""Drive PPSSPP through its local remote-debugger WebSocket (no keyboard, no focus).

  ppdbg.py launch ISO                start PPSSPP with ISO, wait for the debugger
  ppdbg.py press BTN [count] [gap_ms] [hold_ms]   e.g. circle, cross, start, up, down, ltrigger, rtrigger
  ppdbg.py shot out.png               native 480x272 screenshot of the display buffer
  ppdbg.py run script.txt            lines: "press circle 5 300", "wait 2", "shot out.png"
"""
import sys, os, json, time, subprocess, base64, re
import websocket

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, 'tools', 'ppsspp', 'PPSSPPWindows64.exe')
PORTFILE = os.path.join(ROOT, 'work', 'ppsspp_port.txt')


def find_port():
    """PPSSPP listens on a dynamic port; find it from the process's listening sockets."""
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "$p=(Get-Process PPSSPPWindows64 -EA Stop).Id; "
                          "Get-NetTCPConnection -State Listen -OwningProcess $p | Select -Expand LocalPort"],
                         capture_output=True, text=True).stdout.split()
    return [int(x) for x in out if x.isdigit()]


def connect():
    ports = []
    if os.path.exists(PORTFILE):
        ports.append(int(open(PORTFILE).read()))
    ports += find_port()
    for p in ports:
        try:
            ws = websocket.create_connection('ws://127.0.0.1:%d/debugger' % p, timeout=60,
                                             subprotocols=['debugger.ppsspp.org'])
            open(PORTFILE, 'w').write(str(p))
            return ws
        except Exception:
            continue
    raise SystemExit('PPSSPP debugger not reachable (ports tried: %s)' % ports)


def call(ws, event, **kw):
    kw['event'] = event
    kw.setdefault('ticket', str(time.time()))
    ws.send(json.dumps(kw))
    while True:
        raw = ws.recv()
        try:
            r = json.loads(raw)
        except (ValueError, TypeError):
            continue  # binary/log frames
        if r.get('ticket') == kw['ticket'] or r.get('event') == 'error' or (r.get('event') == event and 'ticket' not in r):
            if r.get('event') == 'error':
                raise RuntimeError(r)
            return r


def press(ws, btn, count=1, gap=300, hold=80):
    """explicit button down / up (the 'press' event drops inputs in some menus)"""
    for _ in range(count):
        call(ws, 'input.buttons.send', buttons={btn: True})
        time.sleep(max(hold, 120) / 1000)
        call(ws, 'input.buttons.send', buttons={btn: False})
        time.sleep(gap / 1000)


def shot(ws, out):
    # window capture (PrintWindow): does not pause emulation or take focus
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    os.path.join(ROOT, 'tools', 'pp.ps1'), 'shot', os.path.abspath(out)], check=True,
                   capture_output=True)
    return out


def match(ref, box, tol=0.12):
    """compare only bright (text-like) pixels of a frame region with the same region of ref.png,
    so a changing background doesn't matter. Returns True when the masks mostly agree."""
    from PIL import Image
    tmp = os.path.join(ROOT, 'work', '_match.png')
    shot(None, tmp)
    r = None
    masks = []
    for f in (tmp, ref):
        im = Image.open(f).convert('L').resize((480, 272))
        r = r or tuple(int(v * (480 if i % 2 == 0 else 272)) for i, v in enumerate(box))
        masks.append([1 if p > 225 else 0 for p in im.crop(r).getdata()])
    on = sum(masks[1]) or 1
    diff = sum(x != y for x, y in zip(*masks))
    return diff / on < tol


def launch(iso):
    subprocess.run(['powershell', '-NoProfile', '-Command', 'Stop-Process -Name PPSSPPWindows64 -Force -EA SilentlyContinue'])
    if os.path.exists(PORTFILE):
        os.remove(PORTFILE)
    time.sleep(1)
    # start minimized and without focus, then park off-screen (see pphide.ps1)
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    subprocess.Popen([EXE, iso], startupinfo=si)
    # visible by default (window shown without focus); PP_HIDE=1 parks it off-screen instead
    script = 'pphide.ps1' if os.environ.get('PP_HIDE') else 'ppshow.ps1'
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    os.path.join(ROOT, 'tools', script)], capture_output=True)
    for _ in range(60):
        time.sleep(1)
        try:
            ws = connect(); ws.close(); return True
        except SystemExit:
            pass
    raise SystemExit('debugger did not come up')


def run(lines):
    for ln in lines:
        a = ln.split()
        if not a or a[0].startswith('#'):
            continue
        if a[0] == 'press':
            ws = connect(); press(ws, a[1], *[int(x) for x in a[2:]]); ws.close()
        elif a[0] == 'wait':
            time.sleep(float(a[1]))
        elif a[0] == 'shot':
            print(shot(None, a[1]))
        elif a[0] == 'waitfor':
            # waitfor ref.png x0 y0 x1 y1 tries [button]: region (fractions of the frame) must match ref
            ref, box, tries = a[1], [float(x) for x in a[2:6]], int(a[6])
            btn = a[7] if len(a) > 7 else None
            for k in range(tries):
                if match(ref, box):
                    print('waitfor ok after', k); break
                if btn:
                    ws = connect(); press(ws, btn); ws.close()
                time.sleep(3)
            else:
                raise SystemExit('waitfor %s: screen never matched' % ref)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'launch':
        launch(sys.argv[2])
    elif c == 'press':
        run(['press ' + ' '.join(sys.argv[2:])])
    elif c == 'shot':
        run(['shot ' + sys.argv[2]])
    elif c == 'run':
        run(open(sys.argv[2]).read().splitlines())
