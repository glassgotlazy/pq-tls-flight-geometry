"""Build the paper's figures and table numbers from the reproducibility package's raw data.
Usage: python3 -I figs.py <repo_dir> <out_dir>"""
import csv, json, collections, statistics as st, math, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import fisher_exact

REPO, OUT = sys.argv[1], sys.argv[2]
D = os.path.join(REPO, 'data')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Liberation Serif'], 'mathtext.fontset': 'stix',
    'font.size': 8, 'axes.labelsize': 8, 'xtick.labelsize': 7.2, 'ytick.labelsize': 7.2,
    'legend.fontsize': 7, 'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42,
    'axes.grid': True, 'grid.color': '#e4e4e0', 'grid.linewidth': 0.5, 'axes.axisbelow': True,
    'axes.edgecolor': '#555555', 'xtick.color': '#333333', 'ytick.color': '#333333',
    'axes.labelcolor': '#222222', 'legend.frameon': False, 'lines.linewidth': 1.4,
})
# fixed categorical order (validated): X25519, one-share hybrid, two-segment default, then other groups
C = {'x': '#2a78d6', 'h1': '#eb6834', 'd': '#1baf7a', 'p256h': '#eda100', 'm768': '#e87ba4',
     'm1024': '#008300', 'p384h': '#6250d6'}
GREY, INK, MUTED = '#b9b8b0', '#222222', '#6b6b66'
W1 = 3.45
G = {'X25519': 'x', 'X25519MLKEM768:X25519': 'h1', 'default': 'd'}
NAME = {'x': 'X25519', 'h1': 'Hybrid, 1 share', 'd': 'Default, 2 seg.'}

def save(fig, name, target=3.47):
    # adjust the canvas so the tight bounding box is exactly one IEEE column wide,
    # so LaTeX includes the figure at 100% and font sizes print as specified
    for _ in range(6):
        fig.canvas.draw()
        w = fig.get_tightbbox(fig.canvas.get_renderer()).width
        if abs(w - target) < 0.005: break
        W, H = fig.get_size_inches(); fig.set_size_inches(W + (target - w), H)
    fig.savefig(os.path.join(OUT, name + '.pdf'), bbox_inches='tight', pad_inches=0.02)
    fig.savefig(os.path.join(OUT, name + '.png'), bbox_inches='tight', pad_inches=0.02, dpi=200)
    plt.close(fig)

def T(R, rmin=200):
    rto = R + max(2 * R, rmin)
    return rto, 1.25 * R, R + rto

# ---------------- load loss data ----------------
big = collections.defaultdict(list)
for x in csv.DictReader(open(os.path.join(D, 'e2big.csv'))):
    if x['ok'] != '1' or not x['label'].startswith('pass=Bbig'): continue
    L = dict(kv.split('=') for kv in x['label'].split(';'))
    big[(int(L['rtt']), float(L['p']), G[x['group_cfg']])].append(float(x['t_tls_ms']))
more = collections.defaultdict(list)
for x in csv.DictReader(open(os.path.join(D, 'e2more.csv'))):
    if x['ok'] != '1': continue
    L = dict(kv.split('=') for kv in x['label'].split(';'))
    more[(L['pass'], int(L['rtt']), float(L['p']), int(L['rto_min']), G[x['group_cfg']])].append(float(x['t_tls_ms']))

def added(src, base_key, key):
    b = st.median(src[base_key]); return [t - b for t in src[key]]

def stalled(d, R): return [v for v in d if v > 0.5 * R + 5]

def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h

def boot_mean(a, seed, B=10000):
    g = np.random.default_rng(seed); a = np.asarray(a)
    m = np.sort(a[g.integers(0, len(a), (B, len(a)))].mean(1)); return m[int(.025 * B)], m[int(.975 * B)]

numbers = {}

# ---------------- Fig. 1: repair-path timelines ----------------
R = 50; rto, rack, tail = T(R)
fig, ax = plt.subplots(figsize=(W1, 1.1))
rows = [
    ('One segment, lost', C['x'], [], rto, r'RTO'),
    ('Two segments, head lost', C['d'], [(R, 'SACK of tail')], rack, r'RACK: $\approx 1.25R$'),
    ('Two segments, tail lost', C['d'], [(R, 'ACK of head restarts RTO')], tail, r'$R+T_{\mathrm{RTO}}$'),
]
for i, (lab, col, ev, tr, rl) in enumerate(rows):
    y = 2 - i
    ax.plot([0, tr], [y, y], color=col, lw=3.2, alpha=0.35, solid_capstyle='butt', zorder=2)
    ax.plot(0, y, marker='>', color=INK, ms=4, zorder=3)
    for t, txt in ev:
        ax.plot([t, t], [y - 0.13, y + 0.13], color=INK, lw=0.9, zorder=3)
        ax.text(t, y - 0.2, txt, fontsize=6.6, color=MUTED, va='top', ha='center')
    ax.plot(tr, y, marker='o', ms=5.5, color=col, mec='white', mew=0.8, zorder=4)
    ax.text(tr + 7, y + 0.02, f'{rl} = {tr:g} ms', fontsize=6.6, color=INK, va='bottom', linespacing=1.0)
    ax.text(-6, y, lab, ha='right', va='center', fontsize=7, color=INK)
ax.set_ylim(-0.65, 2.5); ax.set_xlim(0, 500); ax.set_yticks([])
ax.spines['left'].set_visible(False); ax.grid(False)
ax.set_xlabel('Time since ClientHello sent (ms), $R$ = 50 ms')
ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
save(fig, 'fig1_timeline')

# ---------------- Fig. 3: real profiles vs MSS ----------------
br = list(csv.DictReader(open(os.path.join(D, 'browsers_real.csv'))))
bj = json.load(open(os.path.join(D, 'browsers.json')))
def ks_bytes(shares): return sum(4 + int(s.split('/')[1]) for s in shares.split(';'))
e3 = list(csv.DictReader(open(os.path.join(D, 'e3.csv'))))
def e3W(mode, g):
    r = [r for r in e3 if r['label'] == 'srv=dhe;cli_pskke=0' and r['mode'] == mode and r['group_cfg'] == g][0]
    return int(r['ch_len']) + 5, int(r['ch_ks_bytes'])
prof = []
for g, nm in [('X25519MLKEM768:X25519', 'OpenSSL 3.5.4, one share'), ('default', 'OpenSSL 3.5.4, default')]:
    Wf, ks = e3W('full', g); Wr, _ = e3W('resumed', g)
    prof.append((nm, Wf, ks, 0, 0, None)); prof.append((nm.replace('3.5.4, ', '') + ', resumed', Wr, ks, 0, Wr - Wf, None))
for nm, key in [('Chrome 131 (fingerprint)', 'chrome131'), ('Chrome 146 (fingerprint)', 'chrome146')]:
    v = bj[key]; prof.append((nm, v['W'], sum(4 + s[1] for s in v['shares']), v['ech'][0], 0, None))
for nm, lab in [('Chromium 141 (real build)', 'pw-chromium'), ('Edge 154 (real build)', 'edge')]:
    rs = [r for r in br if r['label'] == lab]; Ws = sorted(int(r['W']) for r in rs)
    med = Ws[len(Ws) // 2]; r0 = [r for r in rs if int(r['W']) == med][0]
    prof.append((nm, med, ks_bytes(r0['key_shares']), int(r0['ech_len']), 0, (Ws[0], Ws[-1])))
numbers['browsers_real_range'] = (min(int(r['W']) for r in br), max(int(r['W']) for r in br))
fig, ax = plt.subplots(figsize=(W1, 1.7))
seen = {}
for i, (nm, Wt, ks, ech, psk, rng) in enumerate(prof[::-1]):
    other = Wt - ks - ech - psk; left = 0
    for val, col, lab in [(ks, C['x'], 'Key shares'), (ech, C['h1'], 'ECH (GREASE)'), (psk, C['p256h'], 'pre_shared_key'), (other, GREY, 'Rest of record')]:
        if val <= 0: continue
        b = ax.barh(i, val - 2, left=left, height=0.62, color=col); seen.setdefault(lab, b)
        left += val
    if rng: ax.plot(rng, [i, i], color=INK, lw=0.8, marker='|', ms=5)
    ax.text(max(Wt, rng[1] if rng else 0) + 14, i, f'{Wt:,}' + (' (median)' if rng else ''), va='center', fontsize=6.6, color=INK)
ax.set_yticks(range(len(prof))); ax.set_yticklabels([p[0] for p in prof[::-1]], fontsize=6.8)
for m, lab in [(1448, '1,448'), (1348, '1,348'), (1228, '1,228')]:
    ax.axvline(m, color=INK, lw=0.7, ls=(0, (3, 2)), zorder=5)
    ax.text(m + 14, len(prof) - 0.5, lab, ha='left', va='bottom', fontsize=6.5, color=MUTED, rotation=90)
ax.text(1205, len(prof) - 0.3, 'MSS', ha='right', va='bottom', fontsize=6.5, color=MUTED)
ax.set_xlim(0, 2300); ax.set_ylim(-0.6, len(prof) + 1.05)
ax.set_xlabel('First TLS record $W$ (bytes)'); ax.grid(axis='y', visible=False)
order = ['Key shares', 'ECH (GREASE)', 'pre_shared_key', 'Rest of record']
ax.legend([seen[k] for k in order], order, loc='lower center', bbox_to_anchor=(0.38, -0.5), ncol=2, handlelength=1.0, columnspacing=1.2)
save(fig, 'fig3_profiles')

# ---------------- Fig. 4: headroom vs SNI length ----------------
e1 = list(csv.DictReader(open(os.path.join(D, 'e1.csv'))))
cfgs = [('X25519MLKEM768:X25519', 'h1', 'X25519MLKEM768, 1 share'), ('default', 'd', 'OpenSSL default'),
        ('SecP256r1MLKEM768', 'p256h', 'SecP256r1MLKEM768'), ('MLKEM768', 'm768', 'MLKEM768'),
        ('MLKEM1024', 'm1024', 'MLKEM1024'), ('SecP384r1MLKEM1024', 'p384h', 'SecP384r1MLKEM1024')]
fig, ax = plt.subplots(figsize=(W1, 1.35))
mk = ['o', 's', '^', 'D', 'v', 'P']
for (g, k, lab), m in zip(cfgs, mk):
    pts = sorted({(int(r['sni_len']), int(r['ch_len']) + 5) for r in e1 if r['group_cfg'] == g and r['mtu'] == '1500'})
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=C[k], marker=m, ms=3.6, mec='white', mew=0.5, lw=1.2, label=lab)
for mss, lab in [(1448, 'MSS 1,448 (MTU 1500)'), (1348, 'MSS 1,348 (MTU 1400)'), (1228, 'MSS 1,228 (MTU 1280)')]:
    ax.axhline(mss, color=INK, lw=0.7, ls=(0, (3, 2)))
    ax.text(64.8, mss, f'{mss:,}', ha='left', va='center', fontsize=6.5, color=MUTED, clip_on=False)
ax.axvline(18, color=C['h1'], lw=0.6, ls=':')
ax.annotate('one-share limit:\n18-byte SNI', xy=(18, 1448), xytext=(36, 1252), fontsize=6.6, color=INK,
            arrowprops=dict(arrowstyle='-', lw=0.5, color=MUTED))
ax.set_xlabel('SNI hostname length (bytes)'); ax.set_ylabel('$W$ (bytes)')
ax.set_xlim(0, 64); ax.set_ylim(1180, 1960)
ax.legend(loc='lower center', bbox_to_anchor=(0.45, 1.0), ncol=2, handlelength=1.4, labelspacing=0.2, columnspacing=1.2, fontsize=6.8, borderpad=0.1)
save(fig, 'fig4_sni')

# ---------------- Fig. 5 + Table V numbers ----------------
RTTS = [20, 50, 100, 200]
tab5 = []
pvals = []
for R in RTTS:
    row = {'R': R}
    dd = {}
    for k in ['x', 'h1', 'd']:
        dd[k] = added(big, (R, 0.0, k), (R, 0.05, k))
        row['stall_' + k] = len(stalled(dd[k], R)) / len(dd[k])
        row['mean_' + k] = st.mean(dd[k])
    one = dd['x'] + dd['h1']
    k2, n2 = len(stalled(dd['d'], R)), len(dd['d']); k1, n1 = len(stalled(one, R)), len(one)
    pv = fisher_exact([[k2, n2 - k2], [k1, n1 - k1]], alternative='greater')[1]
    row['fisher'] = pv; row['stall_one'] = k1 / n1; row['k'] = (k2, n2, k1, n1)
    pvals.append(pv); tab5.append(row)
# Holm over the four RTTs
order = np.argsort(pvals); holm = [0] * 4; run = 0
for rank, i in enumerate(order):
    run = max(run, min(1, (4 - rank) * pvals[i])); holm[i] = run
for r, h in zip(tab5, holm): r['holm'] = h
# ratios and CIs from the committed analysis output (exact reproduction of big.py)
ratio = {20: (1.34, 1.09, 1.65, '0.0036'), 50: (1.22, 0.99, 1.50, '0.0312'), 100: (1.72, 1.42, 2.07, '<0.0001'),
         200: (1.92, 1.58, 2.33, '<0.0001')}
for r in tab5: r['ratio'] = ratio[r['R']]
numbers['table5'] = tab5

def model_ratio(R, p=0.05, rmin=200):
    rto, rk, tl = T(R, rmin); e1_ = p * rto; e2_ = p * (1 - p) * (rk + tl) + 2 * p * p * rto; return e2_ / e1_, e1_, e2_

fig, (a1, a2) = plt.subplots(1, 2, figsize=(W1, 1.35), gridspec_kw={'wspace': 0.45})
xs = np.arange(4); off = {'x': -0.18, 'h1': 0, 'd': 0.18}; mks = {'x': 'o', 'h1': 's', 'd': 'D'}
for k in ['x', 'h1', 'd']:
    ys = []; lo = []; hi = []
    for r in tab5:
        n = 2000; kk = round(r['stall_' + k] * n); l, h = wilson(kk, n); ys.append(100 * kk / n); lo.append(100 * l); hi.append(100 * h)
    ys = np.array(ys)
    a1.errorbar(xs + off[k], ys, yerr=[ys - np.array(lo), np.array(hi) - ys], fmt=mks[k], ms=3.6, color=C[k],
                mec='white', mew=0.5, elinewidth=0.8, capsize=0, label=NAME[k])
a1.set_xticks(xs); a1.set_xticklabels(RTTS); a1.set_xlabel('RTT $R$ (ms)'); a1.set_ylabel('Stalled handshakes (%)')
a1.set_ylim(0, 14); a1.text(0.02, 0.98, '(a)', transform=a1.transAxes, va='top', fontsize=7.5)
Rs = np.geomspace(15, 260, 200)
a2.plot(Rs, [model_ratio(r)[0] for r in Rs], color=MUTED, lw=1.0, ls=(0, (4, 2)), label='Model, Eq. (3)')
for i, R in enumerate(RTTS):
    m, l, h, _ = ratio[R]
    a2.errorbar(R, m, yerr=[[m - l], [h - m]], fmt='D', ms=3.6, color=C['d'], mec='white', mew=0.5, elinewidth=0.8, label='Machine 1' if i == 0 else None)
# replications: machine 2 (tb/data/ana2.json, this package) and machine 3 (kernel netem via a forwarding
# namespace; values copied from run2_KN/analysis_output.txt supplied by the authors)
REP = [('Machine 2', 'o', 0.86, [(20, 1.23, 1.00, 1.50), (50, 1.26, 1.02, 1.54)]),
       ('Machine 2, kernel drop', 's', 0.93, [(50, 1.27, 1.03, 1.55)]),
       ('Machine 3, netem', '^', 1.08, [(20, 1.19, 0.97, 1.45), (50, 1.58, 1.27, 1.94)]),
       ('Two VMs, netem', 'v', 1.16, [(50, 1.43, 1.19, 1.71)])]  # two_host_replication_PH (authors' run)
for nm, mk, f, pts in REP:
    for j, (R, m, l, h) in enumerate(pts):
        a2.errorbar(R * f, m, yerr=[[m - l], [h - m]], fmt=mk, ms=3.2, mfc='white', mec=C['d'], color=C['d'], mew=0.8, elinewidth=0.6, alpha=0.9, label=nm if j == 0 else None)
a2.axhline(1, color=INK, lw=0.6)
a2.set_xscale('log'); a2.set_xticks(RTTS); a2.set_xticklabels(RTTS); a2.minorticks_off()
a2.set_xlabel('RTT $R$ (ms)'); a2.set_ylabel('Added-delay ratio'); a2.set_ylim(0.8, 2.45)
a2.text(0.02, 0.98, '(b)', transform=a2.transAxes, va='top', fontsize=7.5)
h1_, l1_ = a1.get_legend_handles_labels(); h2_, l2_ = a2.get_legend_handles_labels()

keep = [k for k, x in enumerate(l2_) if x not in ('Machine 1',)]
fig.legend(h1_ + [h2_[k] for k in keep], l1_ + [l2_[k] for k in keep], loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2, handlelength=1.1, columnspacing=1.5, fontsize=6.8, labelspacing=0.2)
save(fig, 'fig5_loss')

# ---------------- Fig. 6: where stalls land ----------------
fig, axs = plt.subplots(2, 2, figsize=(W1, 1.75), sharey='row', gridspec_kw={'hspace': 0.75, 'wspace': 0.12})
for row, rmin in enumerate([200, 50]):
    for col, R in enumerate([20, 50]):
        ax = axs[row][col]
        if rmin == 200:
            dd = {k: added(big, (R, 0.0, k), (R, 0.05, k)) for k in G.values()}
        else:
            dd = {k: added(more, ('D', R, 0.0, 50, k), ('D', R, 0.05, 50, k)) for k in G.values()}
        one = stalled(dd['x'] + dd['h1'], R); two = stalled(dd['d'], R)
        # per-1,000-handshake normalisation so pass B (2,000) and pass D (1,000) share a scale
        n1 = len(dd['x']) + len(dd['h1']); n2 = len(dd['d'])
        hi = 340 if R == 20 else 380
        bins = np.arange(0, hi + 5, 5)
        ax.hist(one, bins=bins, weights=np.full(len(one), 1000 / n1), histtype='stepfilled', color=C['x'], alpha=0.55, label='One segment (pooled)')
        ax.hist(two, bins=bins, weights=np.full(len(two), 1000 / n2), histtype='step', color=C['d'], lw=1.1, label='Two segments')
        rto, rk, tl = T(R, rmin)
        for v, lab in [(rk, 'RACK'), (rto, 'RTO'), (tl, 'tail')]:
            ax.axvline(v, color=INK, lw=0.6, ls=(0, (2, 2)))
            ax.text(v + 4, 0.97, lab, transform=ax.get_xaxis_transform(), ha='left', va='top', fontsize=6.5, color=MUTED, rotation=90)
        ax.set_xlim(0, hi); ax.grid(axis='x', visible=False)
        ax.set_title(f'$R$ = {R} ms, rto_min = {rmin} ms', fontsize=7.2, pad=3)
        if col == 0: ax.set_ylabel('per 1,000')
        if row == 1: ax.set_xlabel('Added delay (ms)')
h_, l_ = axs[0][0].get_legend_handles_labels(); fig.legend(h_, l_, loc='upper center', bbox_to_anchor=(0.5, 1.07), ncol=2, handlelength=1.4)
save(fig, 'fig6_clusters')

# ---------------- Fig. 7: loss in both directions ----------------
cells = [(50, 0.02), (50, 0.05), (100, 0.05)]
fig, a1 = plt.subplots(figsize=(W1, 1.2))
bw = 0.26; bidir = []
for j, (R, p) in enumerate(cells):
    b0 = st.median(more[('Abig', R, 0.0, 200, 'x')])
    rowd = {'R': R, 'p': p}
    for i, k in enumerate(['x', 'h1', 'd']):
        d = [t - b0 for t in more[('Abig', R, p, 200, k)]]
        m = st.mean(d); l, h = boot_mean(d, 1000 * R + int(100 * p) * 10 + i)
        sr = len(stalled(d, R)) / len(d)
        rowd[k] = (m, l, h, sr)
        a1.bar(j + (i - 1) * bw, m, width=bw - 0.03, color=C[k], label=NAME[k] if j == 0 else None)
        a1.errorbar(j + (i - 1) * bw, m, yerr=[[m - l], [h - m]], color=INK, elinewidth=0.7, capsize=0, fmt='none')
        if k == 'd' or True: a1.text(j + (i - 1) * bw, h + 3, f'{100*sr:.0f}%', ha='center', va='bottom', fontsize=6.5, color=INK)
    one = [t - b0 for k in ['x', 'h1'] for t in more[('Abig', R, p, 200, k)]]
    rowd['stall_one'] = len(stalled(one, R)) / len(one)
    bidir.append(rowd)
numbers['bidir'] = bidir
labs = [f'R = {R} ms, {int(100*p)}% loss' for R, p in cells]
a1.set_xticks(range(3)); a1.set_xticklabels(labs, fontsize=7); a1.grid(axis='x', visible=False)
a1.set_ylabel('Mean added delay (ms)'); a1.set_ylim(0, 110)
a1.legend(loc='upper left', ncol=1, handlelength=1.0, fontsize=7)
save(fig, 'fig7_bidir')

# ---------------- Fig. 8: resumption ----------------
e3 = list(csv.DictReader(open(os.path.join(D, 'e3.csv'))))
def e3row(lab, mode, g):
    return [r for r in e3 if r['label'] == lab and r['mode'] == mode and r['group_cfg'] == g][0]
bars = []
for g, nm in [('X25519MLKEM768:X25519', 'One share'), ('default', 'Default')]:
    f = e3row('srv=dhe;cli_pskke=0', 'full', g); r = e3row('srv=dhe;cli_pskke=0', 'resumed', g)
    Wf, Wr = int(f['ch_len']) + 5, int(r['ch_len']) + 5; ks = int(f['ch_ks_bytes'])
    bars.append((f'{nm}, full', Wf, ks, 0)); bars.append((f'{nm}, resumed', Wr, ks, Wr - Wf))
numbers['resumption'] = bars
sh_dhe = int(e3row('srv=dhe;cli_pskke=1', 'resumed', 'X25519MLKEM768:X25519')['sh_len'])
sh_ke = int(e3row('srv=prefer_pskke;cli_pskke=1', 'resumed', 'X25519MLKEM768:X25519')['sh_len'])
numbers['sh'] = (sh_dhe, sh_ke)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W1, 1.2), gridspec_kw={'width_ratios': [3.0, 1.15], 'wspace': 0.7})
for i, (nm, Wt, ks, psk) in enumerate(bars[::-1]):
    left = 0
    for val, col, lab in [(ks, C['x'], 'Key shares'), (psk, C['p256h'], 'pre_shared_key'), (Wt - ks - psk, GREY, 'Rest')]:
        if val <= 0: continue
        a1.barh(i, val - 2, left=left, height=0.62, color=col, label=lab); left += val
    a1.text(Wt + 15, i, f'{Wt:,}', va='center', fontsize=6.2)
a1.axvline(1448, color=INK, lw=0.7, ls=(0, (3, 2)))
a1.text(1448, 3.55, 'MSS 1,448', ha='center', fontsize=5.8, color=MUTED)
a1.set_yticks(range(4)); a1.set_yticklabels([b[0] for b in bars[::-1]], fontsize=6.6)
a1.set_xlim(0, 2000); a1.set_ylim(-0.5, 4.0); a1.set_xlabel('ClientHello record $W$ (bytes)'); a1.grid(axis='y', visible=False)
h, l = a1.get_legend_handles_labels(); seen = {}
for x_, y_ in zip(h, l): seen.setdefault(y_, x_)
a1.legend(seen.values(), seen.keys(), loc='lower center', bbox_to_anchor=(0.6, -0.62), ncol=3, handlelength=1.0)
a2.bar([0, 1], [sh_dhe, sh_ke], color=[C['h1'], GREY], width=0.6)
for x_, v in zip([0, 1], [sh_dhe, sh_ke]): a2.text(x_, v + 25, f'{v:,}', ha='center', fontsize=6.2)
a2.set_xticks([0, 1]); a2.set_xticklabels(['dhe_ke', 'ke'], fontsize=6.2); a2.set_xlabel('psk mode', fontsize=6.6)
a2.set_ylabel('ServerHello (bytes)'); a2.set_ylim(0, 1400); a2.grid(axis='x', visible=False)
save(fig, 'fig8_resumption')

# ---------------- model table ----------------
numbers['model'] = [(R,) + T(R) + model_ratio(R)[1:] + (model_ratio(R)[0],) for R in RTTS]
json.dump(numbers, open(os.path.join(OUT, 'numbers.json'), 'w'), indent=1, default=float)
print(json.dumps(numbers, indent=1, default=float))
