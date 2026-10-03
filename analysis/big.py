"""Pass B at 2,000 handshakes per configuration and cell (data/e2big.csv): stall clusters,
bootstrap CIs and permutation tests for paper Tables VI-VII.

Usage (from the repository root):  python3 analysis/big.py [path/to/e2big.csv] > analysis/big_output.txt

Randomness: every (R, p) cell gets its own generator, numpy.random.default_rng(1000*R + round(100*p)),
so a cell's CIs and p-values do not depend on which other cells exist or on their order.
Within a cell the generator is used in a fixed order: bootstrap of default/one-segment, permutation
test of default vs one-segment, bootstrap of one-share hybrid/X25519.
Requires numpy.
"""
import csv, collections, json, os, statistics as st, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'e2big.csv')
CTR = os.path.join(os.path.dirname(os.path.abspath(CSV)), 'e2big_ctr.jsonl')
B_BOOT = 10_000   # bootstrap resamples
B_PERM = 10_000   # permutations
CHUNK = 500       # resamples per vectorized chunk

c = collections.defaultdict(list)
for x in csv.DictReader(open(CSV)):
    if x['ok'] != '1' or not x['label'].startswith('pass=Bbig'): continue
    R = int(x['label'].split('rtt=')[1].split(';')[0]); p = float(x['label'].split('p=')[1].split(';')[0])
    c[(R, p, x['group_cfg'])].append(float(x['t_tls_ms']))

def pct(v, q): v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))]

def boot_ratio(rng, a, b, B=B_BOOT):
    """Percentile bootstrap CI of mean(a)/mean(b); a and b resampled independently."""
    a = np.asarray(a); b = np.asarray(b); r = []
    for s in range(0, B, CHUNK):
        k = min(CHUNK, B - s)
        ma = a[rng.integers(0, len(a), (k, len(a)))].mean(axis=1)
        mb = b[rng.integers(0, len(b), (k, len(b)))].mean(axis=1)
        r.append(np.where(mb > 0, ma / np.where(mb > 0, mb, 1), np.nan))
    r = np.sort(np.concatenate(r))
    return r[int(.025 * B)], r[int(.975 * B)]

def perm_p(rng, a, b, B=B_PERM):
    """One-sided permutation test of mean(a) > mean(b). Returns (k, p) with k = #permutations whose
    difference is >= the observed one and p = (k+1)/(B+1)."""
    a = np.asarray(a); b = np.asarray(b); n = len(a)
    obs = a.mean() - b.mean(); pool = np.concatenate([a, b]); k = 0
    for s in range(0, B, CHUNK):
        m = min(CHUNK, B - s)
        P = rng.permuted(np.tile(pool, (m, 1)), axis=1)
        k += int((P[:, :n].mean(axis=1) - P[:, n:].mean(axis=1) >= obs).sum())
    return k, (k + 1) / (B + 1)

print(f'# big.py: {os.path.relpath(CSV)}; bootstrap B={B_BOOT}, permutations B={B_PERM}, '
      f'per-cell seed = 1000*R + round(100*p); numpy {np.__version__}')
for R in [20, 50, 100, 200]:
    for p in [0.05, 0.10]:
        if (R, p, 'default') not in c: continue
        rng = np.random.default_rng(1000 * R + round(100 * p))
        rto = R + max(2 * R, 200); row = {'R': R, 'p': p}
        for g, nm in [('X25519', 'x'), ('X25519MLKEM768:X25519', 'h1'), ('default', 'd')]:
            b = st.median(c[(R, 0.0, g)]); d = [t - b for t in c[(R, p, g)]]
            head = [v for v in d if 0.9 * R < v < 2.2 * R and v < 0.8 * rto]; tail = [v for v in d if abs(v - (R + rto)) < 0.12 * (R + rto)]; rtoc = [v for v in d if abs(v - rto) < 0.08 * rto]
            stall = sum(1 for v in d if v > 0.5 * R + 5) / len(d)
            row[nm] = dict(n=len(d), mean=st.mean(d), stall=stall, p99=pct(c[(R, p, g)], .99), head=(len(head), st.median(head) if head else 0), rto=(len(rtoc), st.median(rtoc) if rtoc else 0), tail=(len(tail), st.median(tail) if tail else 0), d=d)
        one = row['x']['d'] + row['h1']['d']
        row['ratio'] = st.mean(row['d']['d']) / st.mean(one); row['ci'] = boot_ratio(rng, row['d']['d'], one)
        row['k'], row['perm'] = perm_p(rng, row['d']['d'], one)
        row['ratio_h1x'] = st.mean(row['h1']['d']) / st.mean(row['x']['d']); row['ci_h1x'] = boot_ratio(rng, row['h1']['d'], row['x']['d'])
        for nm in ['x', 'h1', 'd']:
            r = row[nm]; print(f"R={R:3} p={p:.2f} {nm:2} n={r['n']} mean={r['mean']:6.1f} stall={100*r['stall']:4.1f}% p99={r['p99']:6.0f} rto={r['rto'][0]}@{r['rto'][1]:.0f} head={r['head'][0]}@{r['head'][1]:.0f} tail={r['tail'][0]}@{r['tail'][1]:.0f}")
        ptxt = '< 0.0001' if row['k'] == 0 else f"{row['perm']:.4f}"
        print(f"   ratio default/one-seg = {row['ratio']:.2f} [{row['ci'][0]:.2f},{row['ci'][1]:.2f}] perm p={ptxt} (k={row['k']}/{B_PERM}, (k+1)/(B+1)={row['perm']:.5f})   hybrid1/x25519 = {row['ratio_h1x']:.2f} [{row['ci_h1x'][0]:.2f},{row['ci_h1x'][1]:.2f}]")
if os.path.exists(CTR):
    for l in open(CTR): print(l.strip())
