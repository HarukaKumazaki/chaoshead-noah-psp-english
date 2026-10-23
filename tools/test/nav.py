import sys,time; sys.path.insert(0,'tools'); sys.path.insert(0,'work'); import ppdbg, menu_sel as M
def press(b,hold=200):
    ws=ppdbg.connect(); ppdbg.press(ws,b,1,600,hold); ws.close(); time.sleep(0.6)
def title_item(target):
    for _ in range(25):
        s,v=M.sel()
        if max(v)<100: press('start'); time.sleep(2); continue
        if s==target: press('circle'); time.sleep(3); return True
        press('down' if (target-s)%4<=2 else 'up')
    return False
if __name__=='__main__':
    print(title_item(int(sys.argv[1])))
    ws=ppdbg.connect(); ppdbg.shot(ws,sys.argv[2])
