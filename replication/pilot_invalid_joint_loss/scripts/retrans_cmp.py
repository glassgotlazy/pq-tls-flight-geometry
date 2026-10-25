import csv,sys,collections,statistics as st
c=collections.defaultdict(list)
for x in csv.DictReader(open(sys.argv[1])):
    if x['ok']!='1' or not x['label'].startswith('pass=Bbig'): continue
    R=int(x['label'].split('rtt=')[1].split(';')[0]); p=float(x['label'].split('p=')[1].split(';')[0])
    if R in (20,50): c[(R,p,x['group_cfg'])].append(x)
for R in (20,50):
    for g in ('X25519','X25519MLKEM768:X25519','default'):
        b=st.median(float(r['t_tls_ms']) for r in c[(R,0.0,g)])
        s=[int(r['retrans']) for r in c[(R,0.05,g)] if float(r['t_tls_ms'])-b>0.5*R+5]
        print(f"paper R={R} {g[:10]:10} stalls={len(s)} retrans_mean={st.mean(s):.2f} dist={dict(sorted(collections.Counter(s).items()))}")
