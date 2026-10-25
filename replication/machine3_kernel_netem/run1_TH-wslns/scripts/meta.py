import json,glob,os,re,sys,hashlib
OUT=sys.argv[1]; RUN=os.path.dirname(OUT)
kv=lambda f: dict(l.strip().split('=',1) for l in open(f) if '=' in l)
o=kv(os.path.join(OUT,'orig_state.txt')); a=kv(os.path.join(OUT,'after_teardown.txt'))
pings={}
for f in sorted(glob.glob(os.path.join(OUT,'ping_*.txt'))):
    L=open(f).read().splitlines(); pings[os.path.basename(f)[5:-4]]={'qdisc':[l for l in L if l.startswith('qdisc')],'summary':L[-2:]}
meta={
 'setup':'SINGLE-HOST STAND-IN: WSL2 VM, two network namespaces (nsA client, nsB server) joined by veth; NOT two physical hosts',
 'label_pass':'TH-wslns','kernel':o['kernel'],'cpus':int(o['cpus']),'distro':'Ubuntu 26.04 LTS (WSL2)',
 'nic':{'A':'vA (veth, in nsA, 10.77.0.1/24)','B':'vB (veth, in nsB, 10.77.0.2/24)','mtu':1500},
 'offloads_set':{'vA':{'gso':'off','tso':'off','gro':'off'},'vB':{'gso':'off','tso':'off','gro':'off'}},
 'sysctls_root_ns_before':{k[7:]:v for k,v in o.items() if k.startswith('rootns.')},
 'sysctls_root_ns_after':{k[7:]:v for k,v in a.items() if k.startswith('rootns.')},
 'sysctls_test_ns':{k:v for k,v in o.items() if k.startswith(('nsA.','nsB.'))},
 'rto_min':'default (200 ms), no route override',
 'netem':'A egress: delay R/2 [loss p] limit 10000; B egress: delay R/2 limit 10000',
 'baseline_rtt_50_pings':open(os.path.join(OUT,'baseline_ping.txt')).read().strip().splitlines(),
 'ping_checks_per_cell':pings,
 'openssl':'OpenSSL 3.5.4 30 Sep 2025 at /opt/ossl35 (pre-existing install; not rebuilt, tarball SHA-256 not verified in this session)',
 'probe':{'source':'testbed/hs.c from pq-tls-flight-geometry repo copy (hs2.c unavailable)','sha256':hashlib.sha256(open(os.path.join(RUN,'src','hs.c'),'rb').read()).hexdigest()},
 'teardown':a,
 'validity_warning':'d (two-segment ClientHello) segments were dropped jointly by netem (stalled d handshakes retransmit ~2 segments; d stall rate ~= one-segment rate). Two-segment results do not measure independent per-packet loss. See SUMMARY.md.',
}
json.dump(meta,open(os.path.join(RUN,'meta.json'),'w'),indent=1); print('meta.json written')
