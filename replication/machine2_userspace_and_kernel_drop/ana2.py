"""Analysis of the second-host replication (B2), kernel-loss variant (K) and resumption timing (S).
Same definitions as analysis/big.py: added delay = t_tls - median(t_tls at p=0, same config);
stall if added > 0.5R + 5 ms; head/RTO/tail clusters by the same windows; percentile bootstrap (10,000)
and one-sided permutation test (10,000). Usage: python3 -I ana2.py <datadir>"""
import csv, collections, statistics as st, sys, os, json, zlib
import numpy as np
from scipy.stats import fisher_exact
D = sys.argv[1]; B = 10000
def load(f, mode=None):
    c = collections.defaultdict(list)
    for x in csv.DictReader(open(os.path.join(D, f))):
        if x['ok'] != '1': continue
        if mode and x['mode'] != mode: continue
        if mode == 'resumed' and x['reused'] != '1': continue
        L = dict(kv.split('=') for kv in x['label'].split(';'))
        c[(int(L['rtt']), float(L['p']), L['cfg'])].append(float(x['t_tls_ms']))
    return c
def rng(k): return np.random.default_rng(zlib.crc32(k.encode()))
def boot_ratio(a, b, key):
    g = rng(key); a = np.asarray(a); b = np.asarray(b)
    r = np.sort(a[g.integers(0, len(a), (B, len(a)))].mean(1) / b[g.integers(0, len(b), (B, len(b)))].mean(1))
    return r[int(.025 * B)], r[int(.975 * B)]
def perm(a, b, key):
    g = rng(key + 'p'); a = np.asarray(a); b = np.asarray(b); pool = np.concatenate([a, b]); n = len(a); obs = a.mean() - b.mean(); k = 0
    for i in range(0, B, 500):
        P = g.permuted(np.tile(pool, (500, 1)), axis=1); k += int((P[:, :n].mean(1) - P[:, n:].mean(1) >= obs).sum())
    return (k + 1) / (B + 1)
def clusters(d, R):
    rto = R + max(2 * R, 200)
    head = [v for v in d if 0.9 * R < v < 2.2 * R and v < 0.8 * rto]
    tail = [v for v in d if abs(v - (R + rto)) < 0.12 * (R + rto)]
    rtoc = [v for v in d if abs(v - rto) < 0.08 * rto]
    f = lambda z: f'{len(z)}@{st.median(z):.0f}' if z else '0@-'
    return f'head={f(head)} rto={f(rtoc)} tail={f(tail)}'
res = {}
def cell(tag, c, R, two, ones):
    add = {k: [t - st.median(c[(R, 0.0, k)]) for t in c[(R, 0.05, k)]] for k in [two] + ones}
    out = {}
    for k, d in add.items():
        out[k] = dict(n=len(d), mean=st.mean(d), stall=sum(v > 0.5 * R + 5 for v in d) / len(d),
                      p90=float(np.percentile(d, 90)), clusters=clusters(d, R))
    one = [v for k in ones for v in add[k]]; dd = add[two]
    lo, hi = boot_ratio(dd, one, f'{tag}{R}')
    k2 = sum(v > 0.5 * R + 5 for v in dd); k1 = sum(v > 0.5 * R + 5 for v in one)
    fp = fisher_exact([[k2, len(dd) - k2], [k1, len(one) - k1]], alternative='greater')[1]
    out['ratio'] = (st.mean(dd) / st.mean(one), lo, hi); out['perm_p'] = perm(dd, one, f'{tag}{R}')
    out['stall_two_vs_one'] = (k2 / len(dd), k1 / len(one), fp)
    print(f'== {tag} R={R}: two={two} vs pooled {ones}')
    for k in [two] + ones:
        o = out[k]; print(f"  {k:8} n={o['n']} mean={o['mean']:6.1f} stall={100*o['stall']:4.1f}% p90={o['p90']:6.1f} {o['clusters']}")
    r = out['ratio']; s = out['stall_two_vs_one']
    print(f"  ratio={r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}] perm p={out['perm_p']:.4f}  stall {100*s[0]:.1f}% vs {100*s[1]:.1f}% Fisher p={s[2]:.2e}")
    res[f'{tag}{R}'] = out
b2 = load('b2.csv')
for R in [20, 50]: cell('B2', b2, R, 'd', ['x', 'h1'])
k = load('k.csv'); cell('K', k, 50, 'd', ['x', 'h1'])
s = load('s.csv', mode='resumed')
cell('S_vs_x_share', s, 50, 'h1', ['h1_to_x'])
cell('S_vs_classical', s, 50, 'h1', ['x'])
json.dump(res, open(os.path.join(D, 'ana2.json'), 'w'), indent=1, default=float)
