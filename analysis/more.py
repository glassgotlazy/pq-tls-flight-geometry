# Analysis for pass D (rto_min causal test) and pass Abig (both directions, 2,000 per config). Per-cell seeded.
# Usage (from the repository root):  python3 analysis/more.py [path/to/e2more.csv] > analysis/more_output.txt
import csv, collections, statistics as st, zlib, os, sys
import numpy as np
c=collections.defaultdict(list)
CSV=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','e2more.csv')
for x in csv.DictReader(open(CSV)):
    if x['ok']!='1': continue
    L=dict(kv.split('=') for kv in x['label'].split(';'))
    c[(L['pass'],int(L['rtt']),float(L['p']),int(L['rto_min']),x['group_cfg'])].append(float(x['t_tls_ms']))
def rng(key): return np.random.default_rng(zlib.crc32(key.encode()))
def boot_ratio(a,b,key,B=10000):
    g=rng(key); a=np.array(a); b=np.array(b)
    ma=a[g.integers(0,len(a),(B,len(a)))].mean(1); mb=b[g.integers(0,len(b),(B,len(b)))].mean(1)
    r=np.sort(ma/mb); return r[int(.025*B)], r[int(.975*B)]
def boot_mean(a,key,B=10000):
    g=rng(key); a=np.array(a); m=np.sort(a[g.integers(0,len(a),(B,len(a)))].mean(1)); return m[int(.025*B)],m[int(.975*B)]
def perm(a,b,key,B=10000):
    g=rng(key+'p'); a=np.array(a); b=np.array(b); pool=np.concatenate([a,b]); n=len(a); obs=a.mean()-b.mean(); k=0
    for i in range(0,B,500):
        idx=np.argsort(g.random((500,len(pool))),axis=1); s=pool[idx]; d=s[:,:n].mean(1)-s[:,n:].mean(1); k+=(d>=obs).sum()
    return (k+1)/(B+1)
G=[('X25519','X25519'),('X25519MLKEM768:X25519','Hybrid one share'),('default','Default two seg')]
print('=== PASS D: rto_min = 50 ms, client->server 5% loss ===')
for R in [20,50]:
    rto=R+max(2*R,50); tail=R+rto; head=1.25*R
    print(f'R={R}: predicted T_RTO={rto} T_RACK={head} T_tail={tail}   (default rto_min: T_RTO={R+max(2*R,200)} T_tail={2*R+max(2*R,200)})')
    for g,nm in G:
        b=st.median(c[('D',R,0.0,50,g)]); d=[t-b for t in c[('D',R,0.05,50,g)]]
        rtoc=[v for v in d if abs(v-rto)<0.15*rto]; tl=[v for v in d if abs(v-tail)<0.12*tail and abs(v-rto)>=0.15*rto]; hd=[v for v in d if 0.9*R<v<2.2*R and abs(v-rto)>=0.15*rto]
        lo,hi=boot_mean(d,f'D{R}{g}')
        print(f'  {nm:17} n={len(d)} added={st.mean(d):6.1f} [{lo:.1f},{hi:.1f}] stalled={100*sum(v>0.5*R+5 for v in d)/len(d):4.1f}%  rto-cluster={len(rtoc)}@{st.median(rtoc) if rtoc else 0:.0f}  head={len(hd)}@{st.median(hd) if hd else 0:.0f}  tail={len(tl)}@{st.median(tl) if tl else 0:.0f}')
    one=[t-st.median(c[('D',R,0.0,50,g)]) for g in ['X25519','X25519MLKEM768:X25519'] for t in c[('D',R,0.05,50,g)]]
    dd=[t-st.median(c[('D',R,0.0,50,'default')]) for t in c[('D',R,0.05,50,'default')]]
    lo,hi=boot_ratio(dd,one,f'Dr{R}')
    print(f'  ratio two-seg/one-seg = {st.mean(dd)/st.mean(one):.2f} [{lo:.2f},{hi:.2f}]  perm p={perm(dd,one,f"Dr{R}"):.4f}')
print('=== PASS Abig: both directions, default rto_min, 2,000 per config ===')
for R,p in [(50,0.02),(50,0.05),(100,0.05)]:
    if ('Abig',R,p,200,'default') not in c: continue
    row=[]
    for g,nm in G:
        v=c[('Abig',R,p,200,g)]; lo,hi=boot_mean(v,f'A{R}{p}{g}'); vs=sorted(v)
        row.append(f'{nm}: n={len(v)} mean={st.mean(v):.1f} [{lo:.1f},{hi:.1f}] p50={vs[len(vs)//2]:.1f} p90={vs[int(.9*len(vs))]:.0f} p99={vs[int(.99*len(vs))]:.0f}')
    print(f'R={R} p={p}:'); [print('  '+r) for r in row]
    one=c[('Abig',R,p,200,'X25519')]+c[('Abig',R,p,200,'X25519MLKEM768:X25519')]; dd=c[('Abig',R,p,200,'default')]
    b0=st.median(c[('Abig',R,0.0,200,'X25519')])
    ex1=[t-b0 for t in one]; ex2=[t-b0 for t in dd]
    lo,hi=boot_ratio(ex2,ex1,f'Ar{R}{p}')
    h1=c[('Abig',R,p,200,'X25519MLKEM768:X25519')]; x=c[('Abig',R,p,200,'X25519')]
    lo2,hi2=boot_ratio([t-b0 for t in h1],[t-b0 for t in x],f'Ah{R}{p}')
    print(f'  added-delay ratio two-seg/one-seg = {st.mean(ex2)/st.mean(ex1):.2f} [{lo:.2f},{hi:.2f}] perm p={perm(ex2,ex1,f"Ar{R}{p}"):.4f}   hybrid1/X25519 = {st.mean([t-b0 for t in h1])/st.mean([t-b0 for t in x]):.2f} [{lo2:.2f},{hi2:.2f}]')
