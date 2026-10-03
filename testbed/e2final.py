#!/usr/bin/env python3
# Final E2 driver: pass B (client->server-only loss), pass C (RSA chain), pass A (both directions).
import subprocess, json, time, random, os, csv, io
HS='/home/claude/pqtls/hs'; env=dict(os.environ,LD_LIBRARY_PATH='/opt/ossl35/lib')
CNT=['TCPLossProbes','TCPLossProbeRecovery','TCPTimeouts','TCPSackRecovery','TCPLostRetransmit','TCPFastRetrans']
def ctr():
    t=subprocess.run(['ip','netns','exec','cli','cat','/proc/net/netstat'],capture_output=True,text=True).stdout.splitlines()
    d={}
    for i in range(0,len(t),2):
        k=t[i].split(); v=t[i+1].split()
        if k[0]=='TcpExt:': d=dict(zip(k[1:],map(int,v[1:])))
    return {c:d.get(c,0) for c in CNT}
def setimp(rtt,model,p,dirn):
    if model=='ge':
        pbg=0.5; pgb=p*pbg/(1-p); j=dict(delay_ms=rtt,model='ge',p_gb=pgb,p_bg=pbg)
    else: j=dict(delay_ms=rtt,model='bernoulli',p=p)
    j.update(seed=random.randint(1,10**6),dir=dirn); open('/tmp/imp.json','w').write(json.dumps(j)); time.sleep(1.2)
def server(cert):
    extra='-cert_chain /home/claude/pqtls/rsachain.pem' if cert=='rsa' else ''
    subprocess.run(['./srv_up.sh','X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1',cert,extra],cwd='/home/claude/pqtls')
def cell(out,passname,cert,rtt,model,p,dirn,g,N,first):
    c0=ctr()
    lab=f'pass={passname};cert={cert};rtt={rtt};model={model};p={p};dir={dirn}'
    r=subprocess.run(['ip','netns','exec','cli',HS,'10.9.0.2','4433',g,'www.example.com',str(N),'0',lab],capture_output=True,text=True,env=env).stdout
    c1=ctr(); dl={k:c1[k]-c0[k] for k in CNT}
    lines=r.strip().splitlines()
    with open(out,'a') as f:
        if first: f.write(lines[0]+'\n')
        for l in lines[1:]: f.write(l+'\n')
    with open(out.replace('.csv','_ctr.csv'),'a') as f:
        f.write(json.dumps(dict(label=lab,group=g,N=N,**dl))+'\n')
plan=[]
G3=['X25519','X25519MLKEM768:X25519','default']
for rtt in [20,50,100,200]:
    plan.append(('B','ec',rtt,'bernoulli',0.0,'c2s',50))
    for p in [0.05,0.10]: plan.append(('B','ec',rtt,'bernoulli',p,'c2s',300))
for p in [0.0,0.02,0.05]: plan.append(('C','rsa',50,'bernoulli',p,'both',150))
for rtt,N in [(50,150),(200,100)]:
    for m,p in [('bernoulli',0.0),('bernoulli',0.01),('bernoulli',0.02),('bernoulli',0.05),('bernoulli',0.10),('ge',0.05),('ge',0.10)]:
        plan.append(('A','ec',rtt,m,p,'both',N))
open('/tmp/e2final_status','w').write('start %s\n'%time.ctime())
cur=None
for i,(ps,cert,rtt,m,p,dirn,N) in enumerate(plan):
    if cert!=cur: server(cert); cur=cert
    setimp(rtt,m,p,dirn)
    out=f'/home/claude/pqtls/e2final_{ps}.csv'
    for g in G3:
        first=not os.path.exists(out)
        cell(out,ps,cert,rtt,m,p,dirn,g,N,first)
    open('/tmp/e2final_status','a').write(f'{i+1}/{len(plan)} done {ps} rtt={rtt} {m} p={p} {time.ctime()}\n')
open('/tmp/e2final_status','a').write('FINISHED %s\n'%time.ctime())
