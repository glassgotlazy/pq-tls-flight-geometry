# ana_ph.py — pass PH (two VMware VMs) analysis; identical to ana_wsl.py, adapted from analysis/big.py of pq-tls-flight-geometry.
# Definitions unchanged; B raised to 10,000 for bootstrap and permutation; adds one-sided Fisher test,
# p90, per-cell netstat deltas, dropped-row accounting. Usage: python3 ana_wsl.py <out_dir>
import csv,collections,statistics as st,random,glob,os,sys,math
random.seed(11)
OUT=sys.argv[1]; RTO_MIN=float(sys.argv[2]) if len(sys.argv)>2 else 200.0
c=collections.defaultdict(list); dropped=collections.Counter(); rows=collections.Counter()
for f in sorted(glob.glob(os.path.join(OUT,'raw_*.csv'))):
    for x in csv.DictReader(open(f)):
        lab=dict(kv.split('=',1) for kv in x['label'].split(';'))
        key=(lab['pass'],int(lab['rtt']),float(lab['p']),lab['cfg']); rows[key]+=1
        if x['ok']!='1': dropped[key]+=1; continue
        c[key].append(float(x['t_tls_ms']))
def pct(v,q): v=sorted(v); return v[min(len(v)-1,int(q*len(v)))]
def boot_ratio(a,b,B=10000):
    r=[]
    for _ in range(B):
        ra=random.choices(a,k=len(a)); rb=random.choices(b,k=len(b)); mb=st.mean(rb)
        r.append(st.mean(ra)/mb if mb>0 else float('nan'))
    r.sort(); return r[int(.025*B)],r[int(.975*B)]
def perm_p(a,b,B=10000):
    obs=st.mean(a)-st.mean(b); pool=a+b; n=len(a); k=0
    for _ in range(B):
        random.shuffle(pool); d=st.mean(pool[:n])-st.mean(pool[n:])
        if d>=obs: k+=1
    return (k+1)/(B+1)
def fisher_greater(a,n1,b,n2):
    # one-sided: P(X>=a), X ~ Hypergeom(total=n1+n2, successes=a+b, draws=n1)
    K=a+b; N=n1+n2; lc=lambda n,k: math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
    return min(1.0,sum(math.exp(lc(K,i)+lc(N-K,n1-i)-lc(N,n1)) for i in range(a,min(K,n1)+1)))
def ctr(path):
    h,v=[l.split() for l in open(path)][:2]; return dict(zip(h[1:],map(int,v[1:])))
print('rows read / dropped (ok!=1) per (pass,R,p,cfg):')
for k in sorted(rows): print(f"  {k}: rows={rows[k]} dropped={dropped[k]}")
print(f"total rows={sum(rows.values())} dropped={sum(dropped.values())}\n")
summary=[]
for PASS in sorted({k[0] for k in c}):
  for R in sorted({k[1] for k in c if k[0]==PASS}):
    for p in sorted({k[2] for k in c if k[0]==PASS and k[1]==R and k[2]>0}):
      rto=R+max(2*R,RTO_MIN); row={'R':R,'p':p}
      print(f"=== {PASS} R={R} p={p}  T_RTO={rto:.0f} ms  stall threshold={0.5*R+5:.0f} ms")
      for nm in ['x','h1','d']:
        b=st.median(c[(PASS,R,0.0,nm)]); d=[t-b for t in c[(PASS,R,p,nm)]]
        head=[v for v in d if 0.9*R<v<2.2*R and v<0.8*rto]; tail=[v for v in d if abs(v-(R+rto))<0.12*(R+rto)]; rtoc=[v for v in d if abs(v-rto)<0.08*rto]
        ns=sum(1 for v in d if v>0.5*R+5)
        row[nm]=dict(n=len(d),base=b,mean=st.mean(d),ns=ns,stall=ns/len(d),p90=pct(d,.9),p99=pct(d,.99),head=(len(head),st.median(head) if head else 0),rto=(len(rtoc),st.median(rtoc) if rtoc else 0),tail=(len(tail),st.median(tail) if tail else 0),d=d)
        r=row[nm]; print(f"  {nm:2} n={r['n']} base_median={b:.3f} mean_added={r['mean']:7.2f} stall={100*r['stall']:5.2f}% ({ns}) p90={r['p90']:7.2f} p99={r['p99']:7.1f} head={r['head'][0]}@{r['head'][1]:.1f} rto={r['rto'][0]}@{r['rto'][1]:.1f} tail={r['tail'][0]}@{r['tail'][1]:.1f}")
      one=row['x']['d']+row['h1']['d']; ns1=row['x']['ns']+row['h1']['ns']
      oh=[v for v in one if 0.9*R<v<2.2*R and v<0.8*rto]; ot=[v for v in one if abs(v-(R+rto))<0.12*(R+rto)]
      row['one']=dict(n=len(one),mean=st.mean(one),stall=ns1/len(one),head=(len(oh),st.median(oh) if oh else 0),tail=(len(ot),st.median(ot) if ot else 0))
      row['ratio']=st.mean(row['d']['d'])/st.mean(one); row['ci']=boot_ratio(row['d']['d'],one); row['perm']=perm_p(row['d']['d'],one)
      row['fisher']=fisher_greater(row['d']['ns'],row['d']['n'],ns1,len(one))
      print(f"  pooled x+h1 n={len(one)} mean_added={row['one']['mean']:.2f} stall={100*row['one']['stall']:.2f}% head={len(oh)}@{row['one']['head'][1]:.1f} tail={len(ot)}@{row['one']['tail'][1]:.1f}")
      print(f"  ratio d/(x+h1) = {row['ratio']:.3f} [{row['ci'][0]:.3f},{row['ci'][1]:.3f}]  perm p={row['perm']:.5f}  Fisher(one-sided, stalls) p={row['fisher']:.3g}")
      row['pass']=PASS; summary.append(row)
print('\nnetstat TcpExt deltas on nsA (after - before), per cell:')
for f in sorted(glob.glob(os.path.join(OUT,'ctr_*_before.txt'))):
    a,b=ctr(f.replace('_before','_after')),ctr(f)
    print(f"  {os.path.basename(f)[4:-11]}: "+' '.join(f"{k}={a[k]-b[k]}" for k in ['TCPLossProbes','TCPLossProbeRecovery','TCPTimeouts','TCPSackRecovery']))
print('\nSUMMARY ROWS (Setup | R | Stalled two/one seg (%) | Ratio [95% CI] | perm p | head/tail cluster medians (ms))')
for r in summary:
    print(f"| {r['pass']} p={r['p']} | {r['R']} | {100*r['d']['stall']:.1f} / {100*r['one']['stall']:.1f} | {r['ratio']:.2f} [{r['ci'][0]:.2f}, {r['ci'][1]:.2f}] | {r['perm']:.4f} | d {r['d']['head'][1]:.1f}/{r['d']['tail'][1]:.1f}; x+h1 {r['one']['head'][1]:.1f}/{r['one']['tail'][1]:.1f} |")
