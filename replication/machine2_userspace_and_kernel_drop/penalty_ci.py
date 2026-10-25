"""Bootstrap CIs for the split penalty (two-seg minus pooled one-seg added delay) in pass B and pass D,
plus model predictions from Eq. (3). Usage: python3 -I penalty_ci.py <repo>"""
import csv, collections, statistics as st, sys, os, numpy as np
D = os.path.join(sys.argv[1], 'data')
G = {'X25519': 'x', 'X25519MLKEM768:X25519': 'h1', 'default': 'd'}
c = collections.defaultdict(list)
for f, src in [('e2big.csv', 'B'), ('e2more.csv', 'M')]:
    for x in csv.DictReader(open(os.path.join(D, f))):
        if x['ok'] != '1': continue
        L = dict(kv.split('=') for kv in x['label'].split(';'))
        rmin = int(L.get('rto_min', 200)); ps = L['pass']
        if ps not in ('Bbig', 'D'): continue
        c[(ps, int(L['rtt']), float(L['p']), rmin, G[x['group_cfg']])].append(float(x['t_tls_ms']))
def model(R, rmin, p=0.05):
    rto = R + max(2 * R, rmin); rk = 1.25 * R; tl = R + rto
    e1 = p * rto; e2 = p * (1 - p) * (rk + tl) + 2 * p * p * rto; return e2 - e1
rng = np.random.default_rng(20261025); B = 10000
for R in [20, 50]:
    for ps, rmin in [('Bbig', 200), ('D', 50)]:
        add = {k: np.array(c[(ps, R, 0.05, rmin, k)]) - st.median(c[(ps, R, 0.0, rmin, k)]) for k in G.values()}
        one = np.concatenate([add['x'], add['h1']]); two = add['d']
        pen = two.mean() - one.mean()
        bs = two[rng.integers(0, len(two), (B, len(two)))].mean(1) - one[rng.integers(0, len(one), (B, len(one)))].mean(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f'R={R} rto_min={rmin}: measured penalty {pen:.2f} ms [{lo:.2f}, {hi:.2f}]  model {model(R, rmin):.2f} ms  n2={len(two)} n1={len(one)}')
