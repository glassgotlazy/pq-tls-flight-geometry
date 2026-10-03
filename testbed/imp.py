#!/usr/bin/env python3
"""imp.py — userspace packet impairment engine between two network namespaces via TUN.
Replaces tc-netem (not available in this kernel). Per-direction one-way delay, Bernoulli or
Gilbert-Elliott loss, optional client->server-only loss. Params reloaded from a JSON file."""
import os, fcntl, struct, select, heapq, random, time, json, sys
TUNSETIFF=0x400454ca; IFF_TUN=0x0001; IFF_NO_PI=0x1000
def tun(name):
    fd=os.open('/dev/net/tun',os.O_RDWR)
    fcntl.ioctl(fd,TUNSETIFF,struct.pack('16sH',name.encode(),IFF_TUN|IFF_NO_PI))
    return fd
CFG='/tmp/imp.json'
class Loss:
    def __init__(s,c,seed):
        s.rng=random.Random(seed); s.mode=c.get('model','bernoulli'); s.p=c.get('p',0.0)
        s.gb=c.get('p_gb',0.0); s.bg=c.get('p_bg',1.0); s.bad=False
    def drop(s):
        if s.mode=='ge':
            # Gilbert model: transition first, then lose iff in Bad state
            if s.bad: s.bad = s.rng.random() >= s.bg
            else:     s.bad = s.rng.random() < s.gb
            return s.bad
        return s.rng.random() < s.p
def load():
    try: return json.load(open(CFG)), os.path.getmtime(CFG)
    except Exception: return {'delay_ms':0}, 0
def main():
    a=tun('tunC'); b=tun('tunS')
    print('ready',flush=True)
    cfg,mt=load(); seed=cfg.get('seed',1)
    L={'c2s':Loss(cfg,seed),'s2c':Loss(cfg,seed+7)}
    q=[]; n=0; last=time.time(); stats={'fwd':0,'drop':0}
    while True:
        t=time.monotonic()
        while q and q[0][0]<=t:
            _,_,fd,pkt=heapq.heappop(q); os.write(fd,pkt)
        to=max(0.0,q[0][0]-t) if q else 0.5
        r,_,_=select.select([a,b],[],[],min(to,0.5))
        if time.time()-last>0.3:
            last=time.time()
            try:
                m=os.path.getmtime(CFG)
                if m!=mt:
                    cfg,mt=load(); seed=cfg.get('seed',1)
                    L={'c2s':Loss(cfg,seed),'s2c':Loss(cfg,seed+7)}; stats={'fwd':0,'drop':0}
            except Exception: pass
        for fd in r:
            pkt=os.read(fd,65535); d='c2s' if fd==a else 's2c'; out=b if fd==a else a
            lossy = cfg.get('dir','both')=='both' or cfg.get('dir')==d
            if lossy and L[d].drop(): stats['drop']+=1; continue
            stats['fwd']+=1; n+=1
            heapq.heappush(q,(time.monotonic()+cfg.get('delay_ms',0)/2000.0,n,out,pkt))
main()
