import json,glob,os,sys,hashlib
OUT=sys.argv[1]; RUN=os.path.dirname(OUT)
kv=lambda f: dict(l.strip().split('=',1) for l in open(f) if '=' in l)
o=kv(os.path.join(OUT,'orig_state.txt')); a=kv(os.path.join(OUT,'after_teardown.txt'))
pings={os.path.basename(f)[5:-4]:open(f).read().splitlines() for f in sorted(glob.glob(os.path.join(OUT,'ping_*.txt')))}
meta={
 'setup':'SINGLE-HOST STAND-IN: WSL2 VM, three network namespaces nsA (client) - nsR (router) - nsB (server) joined by veth pairs; NOT two physical hosts',
 'label_pass':'KN','kernel':o['kernel'],'cpus':int(o['cpus']),'distro':'Ubuntu 26.04 LTS (WSL2)',
 'topology':{'nsA':'vA 10.77.1.1/24, default via 10.77.1.254','nsR':'vRa 10.77.1.254/24, vRb 10.77.2.254/24, ip_forward=1','nsB':'vB 10.77.2.2/24, default via 10.77.2.254','mtu':1500},
 'netem':'nsR vRb (toward server): delay R/2 [loss p] limit 10000; nsR vRa (toward client): delay R/2 limit 10000; vA and vB: noqueue (no netem)',
 'offloads_set':'gso off, tso off, gro off on vA, vRa, vRb, vB',
 'settings_verified':open(os.path.join(OUT,'settings.txt')).read().splitlines(),
 'sysctls_root_ns_before':{k[7:]:v for k,v in o.items() if k.startswith('rootns.')},
 'sysctls_root_ns_after':{k[7:]:v for k,v in a.items() if k.startswith('rootns.')},
 'sysctls_test_ns_defaults':{k:v for k,v in o.items() if k.startswith(('nsA.','nsR.','nsB.'))},
 'rto_min':'default (200 ms), no route override',
 'baseline_rtt_50_pings':open(os.path.join(OUT,'baseline_ping.txt')).read().strip().splitlines(),
 'ping_checks_per_cell':pings,
 'clienthello_capture':'out/capture_vRa_in.txt, out/capture_vRb_out.txt: default ClientHello = 2 packets, TCP payload 1448 (SNI present) + 45, before and after netem',
 'openssl':'OpenSSL 3.5.4 30 Sep 2025 at /opt/ossl35 (pre-existing install; not rebuilt, tarball SHA-256 not verified in this session)',
 'probe':{'source':'testbed/hs.c from pq-tls-flight-geometry repo copy (hs2.c unavailable)','sha256':hashlib.sha256(open(os.path.join(RUN,'src','hs.c'),'rb').read()).hexdigest()},
 'teardown':a,
 'criterion3':'partly met: d head cluster at 30.4 ms (R=20) / 68.7 ms (R=50), about +5.5 ms above the 1.25R prediction; tail 246.9 / 318.6 ms; d stalls at T_RTO 2 / 0. Ratio withheld from SUMMARY.md per instruction.',
}
json.dump(meta,open(os.path.join(RUN,'meta.json'),'w'),indent=1); print('meta.json written')
