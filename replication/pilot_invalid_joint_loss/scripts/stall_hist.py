import csv,glob,os,sys,statistics as st,collections
OUT=sys.argv[1]; c=collections.defaultdict(list)
for f in glob.glob(os.path.join(OUT,'raw_*.csv')):
    for x in csv.DictReader(open(f)):
        l=dict(kv.split('=',1) for kv in x['label'].split(';')); c[(int(l['rtt']),float(l['p']),l['cfg'])].append(x)
for R in (20,50):
    for g in ('x','h1','d'):
        b=st.median(float(r['t_tls_ms']) for r in c[(R,0.0,g)])
        s=sorted((round(float(r['t_tls_ms'])-b),int(r['retrans'])) for r in c[(R,0.05,g)] if float(r['t_tls_ms'])-b>0.5*R+5)
        h=collections.Counter(v//10*10 for v,_ in s)
        print(f"R={R} {g:2} stalls={len(s)} retrans_mean={st.mean(t for _,t in s):.2f}  bins(10ms): "+' '.join(f"{k}:{n}" for k,n in sorted(h.items())))
