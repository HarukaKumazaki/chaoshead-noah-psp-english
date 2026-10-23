import sys,time; sys.path.insert(0,'tools'); import ppdbg
ws=ppdbg.connect()
def P(b,n=1,w=0.8): ppdbg.press(ws,b,n,int(w*1000),200)
def S(name): time.sleep(0.6); ppdbg.shot(ws,'work/shots/%s.png'%name)
seq=sys.argv[1:]
for cmd in seq:
    if cmd.startswith('shot:'): S(cmd[5:])
    elif cmd.startswith('wait:'): time.sleep(float(cmd[5:]))
    else:
        b,_,n=cmd.partition('*'); P(b,int(n or 1))
