#!/usr/bin/env python3
"""Second-host replication, kernel-side loss variant, and resumed-handshake timing.
Same probe (hs.c + optional resume_groups), same impairment engine (imp.py), one s_server per stream.
Usage: python3 -I run2.py <tbdir> <phase>   phase in {setup, B2, K, S, all}"""
import subprocess, json, time, random, os, sys
TB = sys.argv[1]; PH = sys.argv[2]
HS = os.path.join(TB, 'hs2'); O = '/opt/ossl35/bin/openssl'
env = dict(os.environ, LD_LIBRARY_PATH='/opt/ossl35/lib', IMP_CFG=os.path.join(TB, 'imp.json'))
G = 'X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1'
DATA = os.path.join(TB, 'data'); os.makedirs(DATA, exist_ok=True)
STATUS = os.path.join(TB, 'status.log')
PORTS = list(range(4501, 4507))
CNT = ['TCPLossProbes', 'TCPLossProbeRecovery', 'TCPTimeouts', 'TCPSackRecovery']

def sh(*a, check=True): return subprocess.run(list(a), check=check, capture_output=True, text=True, env=env).stdout
def log(m): open(STATUS, 'a').write(f'{time.ctime()} {m}\n')
def ctr():
    t = sh('ip', 'netns', 'exec', 'cli', 'cat', '/proc/net/netstat').splitlines()
    for i in range(0, len(t), 2):
        k = t[i].split(); v = t[i + 1].split()
        if k[0] == 'TcpExt:': d = dict(zip(k[1:], map(int, v[1:]))); return {c: d.get(c, 0) for c in CNT}
def imp(**kw): open(env['IMP_CFG'], 'w').write(json.dumps(kw)); time.sleep(1.2)

def setup():
    for ns in ['cli', 'srv']: subprocess.run(['ip', 'netns', 'del', ns], capture_output=True)
    subprocess.run(['pkill', '-f', 'tb/imp.py'], capture_output=True); time.sleep(0.5)
    sh('sysctl', '-w', 'net.ipv4.tcp_congestion_control=cubic')  # new namespaces inherit it
    sh('ip', 'netns', 'add', 'cli'); sh('ip', 'netns', 'add', 'srv')
    imp(delay_ms=0)
    subprocess.Popen(['setsid', 'python3', '-I', os.path.join(TB, 'imp.py')], env=env,
                     stdout=open(os.path.join(TB, 'imp.log'), 'w'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(1.5)
    sh('ip', 'link', 'set', 'tunC', 'netns', 'cli'); sh('ip', 'link', 'set', 'tunS', 'netns', 'srv')
    for ns, dev, ip in [('cli', 'tunC', '10.9.0.1/24'), ('srv', 'tunS', '10.9.0.2/24')]:
        sh('ip', '-n', ns, 'addr', 'add', ip, 'dev', dev); sh('ip', '-n', ns, 'link', 'set', dev, 'mtu', '1500', 'up')
        sh('ip', '-n', ns, 'link', 'set', 'lo', 'up')
        sh('ip', 'netns', 'exec', ns, 'ethtool', '-K', dev, 'gso', 'off', 'tso', 'off', check=False)
    meta = {k: sh('ip', 'netns', 'exec', 'cli', 'sysctl', '-n', k).strip() for k in
            ['net.ipv4.tcp_congestion_control', 'net.ipv4.tcp_early_retrans', 'net.ipv4.tcp_recovery',
             'net.ipv4.tcp_timestamps', 'net.ipv4.tcp_sack']}
    meta['kernel'] = sh('uname', '-r').strip(); meta['nproc'] = sh('nproc').strip()
    meta['openssl'] = sh(O, 'version', check=False).strip()
    meta['gso_tso'] = sh('ip', 'netns', 'exec', 'cli', 'ethtool', '-k', 'tunC', check=False)
    json.dump(meta, open(os.path.join(DATA, 'meta.json'), 'w'), indent=1)
    subprocess.run(['pkill', '-f', 's_server'], capture_output=True); time.sleep(0.3)
    for pt in PORTS:
        subprocess.Popen(['setsid', 'ip', 'netns', 'exec', 'srv', O, 's_server', '-accept', str(pt), '-cert', os.path.join(TB, 'ec.crt'),
                          '-key', os.path.join(TB, 'ec.key'), '-www', '-quiet', '-groups', G], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(2); log('setup done ' + json.dumps({k: v for k, v in meta.items() if k != 'gso_tso'}))

def nft_loss(p):
    subprocess.run(['ip', 'netns', 'exec', 'srv', 'nft', 'delete', 'table', 'inet', 'kl'], capture_output=True)
    if p <= 0: return
    thr = int(round(p * 1000))
    sh('ip', 'netns', 'exec', 'srv', 'nft', 'add', 'table', 'inet', 'kl')
    sh('ip', 'netns', 'exec', 'srv', 'nft', 'add chain inet kl pre { type filter hook prerouting priority -300 ; }')
    sh('ip', 'netns', 'exec', 'srv', 'nft', 'add', 'rule', 'inet', 'kl', 'pre', 'iifname', 'tunS', 'tcp', 'dport', '4501-4506',
       'numgen', 'random', 'mod', '1000', '<', str(thr), 'counter', 'drop')

def run_cell(out, ps, R, p, N, configs, loss='imp', resume=0):
    """configs: list of (group_cfg, resume_groups or None, name). Two streams per config."""
    if loss == 'imp':
        nft_loss(0); imp(delay_ms=R, model='bernoulli', p=p, dir='c2s', seed=random.randint(1, 10**6))
    else:
        imp(delay_ms=R, model='bernoulli', p=0.0, dir='c2s', seed=1); nft_loss(p)
    c0 = ctr(); procs = []
    for j, (g, rg, nm) in enumerate(configs * 2):
        lab = f'pass={ps};rtt={R};p={p};loss={loss};cfg={nm};stream={j // len(configs)}'
        f = open(os.path.join(TB, f'part_{j}.csv'), 'w')
        args = ['ip', 'netns', 'exec', 'cli', HS, '10.9.0.2', str(PORTS[j]), g, 'www.example.com', str(N), str(resume), lab, '0']
        if rg: args.append(rg)
        procs.append((subprocess.Popen(args, stdout=f, stderr=subprocess.DEVNULL, env=env), f))
    for pr, f in procs: pr.wait(); f.close()
    c1 = ctr(); nft_loss(0)
    path = os.path.join(DATA, out); new = not os.path.exists(path)
    with open(path, 'a') as o:
        for j in range(len(procs)):
            L = open(os.path.join(TB, f'part_{j}.csv')).read().strip().splitlines()
            if new: o.write(L[0] + '\n'); new = False
            if len(L) > 1: o.write('\n'.join(L[1:]) + '\n')
    with open(os.path.join(DATA, out.replace('.csv', '_ctr.jsonl')), 'a') as o:
        o.write(json.dumps(dict(pass_=ps, rtt=R, p=p, loss=loss, **{k: c1[k] - c0[k] for k in CNT})) + '\n')
    log(f'cell {ps} R={R} p={p} loss={loss} N={N} done')

G3 = [('X25519', None, 'x'), ('X25519MLKEM768:X25519', None, 'h1'), ('default', None, 'd')]
GS = [('X25519', None, 'x'), ('X25519MLKEM768:X25519', None, 'h1'), ('X25519MLKEM768:X25519', 'X25519', 'h1_to_x')]
if PH in ('setup', 'all'): setup()
if PH in ('B2', 'all'):
    for R in [20, 50]:
        run_cell('b2.csv', 'B2', R, 0.0, 150, G3); run_cell('b2.csv', 'B2', R, 0.05, 1000, G3)
if PH in ('K', 'all'):
    run_cell('k.csv', 'K', 50, 0.0, 150, G3, loss='nft'); run_cell('k.csv', 'K', 50, 0.05, 1000, G3, loss='nft')
if PH in ('S', 'all'):
    run_cell('s.csv', 'S', 50, 0.0, 150, GS, resume=1); run_cell('s.csv', 'S', 50, 0.05, 1000, GS, resume=1)
log(f'phase {PH} FINISHED')
