import csv,collections,statistics as st,sys
r=list(csv.DictReader(open(sys.argv[1])))
cells=collections.OrderedDict()
for x in r:
    cells.setdefault((x['label'],x['group_cfg']),[]).append(x)
base={}
for (lab,g),v in cells.items():
    if 'p=0.0;' in lab: base[(lab.split(';model')[0],g)]=st.median(float(i['t_tls_ms']) for i in v)
for (lab,g),v in cells.items():
    if 'p=0.0;' in lab: continue
    R=int(lab.split('rtt=')[1].split(';')[0]); b=base.get((lab.split(';model')[0],g))
    s=[float(i['t_tls_ms'])-b for i in v]
    fast=[d for d in s if 0.8*R<d<3*R and d<150]; slow=[d for d in s if d>=150]
    t=sorted(s); n=len(s)
    print(f"R={R:3} {lab.split('p=')[1].split(';')[0]:5} {g[:14]:14} n={n} mean_extra={st.mean(s):6.1f} p90={t[int(.9*n)]:6.1f} p99={t[int(.99*n)]:6.1f} fast={len(fast):3}({st.median(fast) if fast else 0:5.0f}) slow={len(slow):3}({st.median(slow) if slow else 0:5.0f})")
