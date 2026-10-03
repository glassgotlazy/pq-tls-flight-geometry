"""Passes A, B (300 handshakes per cell) and C: means with bootstrap 95% CIs and percentiles (paper Table VIII;
the pass B ratios are the "earlier 300-handshake run" quoted in Section VI-B).

Usage (from the repository root):  python3 analysis/final.py > analysis/final_output.txt

Randomness: every cell (pass, R, model, p, group) gets its own generator,
numpy.random.default_rng(zlib.crc32("<pass>|<R>|<model>|<p>|<group>")), so a cell's CI does not depend on
which other cells exist or on their order. Bootstrap: 10,000 resamples, percentile CI.
Requires numpy.
"""
import collections, csv, os, statistics as st, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
B_BOOT = 10_000

def load(f):
    c = collections.OrderedDict()
    for x in csv.DictReader(open(os.path.join(DATA, f))):
        if x['ok'] != '1': continue
        lab = x['label']; key = (int(lab.split('rtt=')[1].split(';')[0]), lab.split('model=')[1].split(';')[0], float(lab.split('p=')[1].split(';')[0]), x['group_cfg'])
        c.setdefault(key, []).append(float(x['t_tls_ms']))
    return c

def rng_for(pas, R, m, p, g):
    return np.random.default_rng(zlib.crc32(f'{pas}|{R}|{m}|{p:.2f}|{g}'.encode()))

def bmean(rng, v, B=B_BOOT):
    """Percentile bootstrap 95% CI of the mean."""
    v = np.asarray(v); s = np.sort(v[rng.integers(0, len(v), (B, len(v)))].mean(axis=1))
    return s[int(.025 * B)], s[int(.975 * B)]

def pct(v, p): v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))]

print(f'# final.py: bootstrap B={B_BOOT}, per-cell seed = crc32("<pass>|<R>|<model>|<p>|<group>"); numpy {np.__version__}')
B = load('e2final_B.csv'); out = {}
print('PASS B (client->server loss)')
for (R, m, p, g), v in B.items():
    if p == 0: continue
    b = st.median(B[(R, m, 0.0, g)]); d = [t - b for t in v]
    rto = R + max(2 * R, 200)
    head = [x for x in d if 0.9 * R < x < 2.2 * R and x < rto * 0.8]; tail = [x for x in d if abs(x - (R + rto)) < 0.12 * (R + rto)]; rtoc = [x for x in d if abs(x - rto) < 0.08 * rto]
    lo, hi = bmean(rng_for('B', R, m, p, g), d); stall = sum(1 for x in d if x > 0.5 * R + 5) / len(d)
    out[(R, p, g)] = st.mean(d)
    print(f"R={R:3} p={p:.2f} {g[:22]:22} n={len(v)} extra_mean={st.mean(d):6.1f} [{lo:5.1f},{hi:5.1f}] stall%={100*stall:4.1f} p99={pct(v,.99):6.0f} head={len(head)}@{st.median(head) if head else 0:4.0f} rto={len(rtoc)}@{st.median(rtoc) if rtoc else 0:4.0f} tail={len(tail)}@{st.median(tail) if tail else 0:4.0f}")
print('ratio default / mean(one-segment)')
for R in [20, 50, 100, 200]:
    for p in [0.05, 0.10]:
        if (R, p, 'default') in out:
            s = (out[(R, p, 'X25519')] + out[(R, p, 'X25519MLKEM768:X25519')]) / 2; print(R, p, round(out[(R, p, 'default')] / s, 2), round(s, 1), round(out[(R, p, 'default')], 1))
for f, nm, pas in [('e2final_C.csv', 'C rsa both', 'C'), ('e2final_A.csv', 'A both', 'A')]:
    print('PASS', nm); c = load(f)
    for (R, m, p, g), v in c.items():
        lo, hi = bmean(rng_for(pas, R, m, p, g), v)
        print(f"R={R} {m:9} p={p:.2f} {g[:22]:22} n={len(v)} mean={st.mean(v):6.1f} [{lo:5.1f},{hi:5.1f}] p50={pct(v,.5):5.1f} p90={pct(v,.9):6.1f} p99={pct(v,.99):6.0f}")
