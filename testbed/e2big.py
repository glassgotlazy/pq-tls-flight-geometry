#!/usr/bin/env python3
# Large pass B: client->server Bernoulli loss, 3 configs x 2 parallel streams x N per stream, one server per stream.
import subprocess, json, time, random, os
HS='/home/claude/pqtls/hs'; env=dict(os.environ,LD_LIBRARY_PATH='/opt/ossl35/lib')
O='/opt/ossl35/bin/openssl'; G='X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1'
CNT=['TCPLossProbes','TCPLossProbeRecovery','TCPTimeouts','TCPSackRecovery']
def ctr():
    t=subprocess.run(['ip','netns','exec','cli','cat','/proc/net/netstat'],capture_output=True,text=True).stdout.splitlines()
    for i in range(0,len(t),2):
        k=t[i].split(); v=t[i+1].split()
        if k[0]=='TcpExt:': d=dict(zip(k[1:],map(int,v[1:]))); return {c:d.get(c,0) for c in CNT}
PORTS=list(range(4501,4507))
for pt in PORTS:
    subprocess.Popen(['setsid','ip','netns','exec','srv',O,'s_server','-accept',str(pt),'-cert','/home/claude/pqtls/ec.crt','-key','/home/claude/pqtls/ec.key','-www','-quiet','-groups',G],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
time.sleep(2)
G3=['X25519','X25519MLKEM768:X25519','default']
plan=[]
for R in [20,50,100,200]:
    plan.append((R,0.0,150)); plan.append((R,0.05,1000))
for R in [20,50,100,200]: plan.append((R,0.10,1000))
out='/home/claude/pqtls/e2big.csv'; first=True
open('/tmp/e2big_status','w').write('start %s\n'%time.ctime())
for i,(R,p,N) in enumerate(plan):
    open('/tmp/imp.json','w').write(json.dumps(dict(delay_ms=R,model='bernoulli',p=p,dir='c2s',seed=random.randint(1,10**6)))); time.sleep(1.2)
    c0=ctr(); procs=[]
    for j,g in enumerate(G3*2):
        lab=f'pass=Bbig;rtt={R};p={p};stream={j//3}'
        f=open(f'/tmp/big_{j}.csv','w')
        procs.append((subprocess.Popen(['ip','netns','exec','cli',HS,'10.9.0.2',str(PORTS[j]),g,'www.example.com',str(N),'0',lab],stdout=f,stderr=subprocess.DEVNULL,env=env),f))
    for pr,f in procs: pr.wait(); f.close()
    c1=ctr()
    with open(out,'a') as o:
        for j in range(6):
            L=open(f'/tmp/big_{j}.csv').read().strip().splitlines()
            if first: o.write(L[0]+'\n'); first=False
            o.write('\n'.join(L[1:])+'\n')
    with open('/home/claude/pqtls/e2big_ctr.jsonl','a') as o: o.write(json.dumps(dict(rtt=R,p=p,**{k:c1[k]-c0[k] for k in CNT}))+'\n')
    open('/tmp/e2big_status','a').write(f'{i+1}/{len(plan)} R={R} p={p} {time.ctime()}\n')
open('/tmp/e2big_status','a').write('FINISHED %s\n'%time.ctime())
