import json,glob,os,sys,hashlib,re
L=sys.argv[1]; A=os.path.join(L,'vm_A'); B=os.path.join(L,'vm_B')
kv=lambda f: dict(l.rstrip('\n').split('=',1) for l in open(f) if '=' in l and not l.startswith('#'))
rd=lambda f: open(f).read().splitlines()
pings={os.path.basename(f)[5:-4]:rd(f) for f in sorted(glob.glob(os.path.join(A,'ping_*.txt')))}
pings_attempt1={os.path.basename(f)[5:-4]:rd(f) for f in sorted(glob.glob(os.path.join(A,'accept_attempt1','ping_*.txt')))}
sha=lambda f: hashlib.sha256(open(f,'rb').read()).hexdigest()
bl=lambda f: [l for l in rd(f) if l.startswith(('sha256','OpenSSL'))]
m={
 'setup':'SINGLE PHYSICAL MACHINE: two VMware Workstation 25.0 VMs (pqa = host A, pqb = host B) on one Windows 11 Home laptop (Intel Core Ultra 5 125H, 15.5 GB RAM), VMware running on the Windows hypervisor. Not two physical hosts.',
 'label_pass':'PH',
 'vms':{'image':'ubuntu-24.04-server-cloudimg-amd64.ova, SHA-256 ce599f89777c6eaa1a3156698f004b7938dcc16680132d5f10da1269770e74a2 (matches Ubuntu SHA256SUMS)',
        'vcpus':2,'ram_mb':1536,'kernel':'6.8.0-147-generic (both)','CONFIG_HZ':1000,'clocksource':'tsc (both)'},
 'nics':{'A':{'mgmt0':'vmxnet3, VMware NAT, 192.168.6.129 (SSH only)','test0':'vmxnet3, VMware LAN segment, 192.168.77.1/24, MTU 1500'},
         'B':{'mgmt0':'vmxnet3, VMware NAT, 192.168.6.130 (SSH only)','test0':'vmxnet3, VMware LAN segment, 192.168.77.2/24, MTU 1500'},
         'A_cli_namespace':'cli: vcli 10.77.0.2/24 default via 10.77.0.1; root: vroot 10.77.0.1/24; ip_forward=1'},
 'offloads':{'A_orig':{k:v for k,v in kv(os.path.join(A,'orig_A.txt')).items() if k.startswith('ethtool')},
             'B_orig':{k:v for k,v in kv(os.path.join(B,'orig_B.txt')).items() if k.startswith('ethtool')},
             'set':'tso, gso, gro, lro off on A test0, vroot, vcli and B test0 (lro on veth is fixed off)',
             'A_during':rd(os.path.join(A,'settings_A.txt')),'B_during':rd(os.path.join(B,'settings_B.txt'))},
 'sysctls':{'A_orig':{k:v for k,v in kv(os.path.join(A,'orig_A.txt')).items() if k.startswith('sysctl')},
            'B_orig':{k:v for k,v in kv(os.path.join(B,'orig_B.txt')).items() if k.startswith('sysctl')}},
 'restored':{'A_after':rd(os.path.join(A,'after_A.txt')),'B_after':rd(os.path.join(B,'after_B.txt')),'diff_vs_orig':'none on either VM'},
 'route_on_B':'10.77.0.0/24 via 192.168.77.1 dev test0 (added with approval, removed at cleanup)',
 'rto_min':'default (200 ms)',
 'netem':'A test0 root: delay 25ms [loss 5%] limit 10000 (c2s); A vroot root: delay 25ms limit 10000 (s2c); none on B',
 'lan_rtt':{'step1_idle_50_pings_200ms':rd(os.path.join(L,'step1_lan_ping_idle.txt'))[1:],
            'diag_200_pings_10ms':rd(os.path.join(L,'diag_ping_10ms.txt'))[-2:]+['p50=0.447 p90=0.801 p99=2.030 ms']},
 'ping_checks_per_cell':pings,'ping_checks_attempt1':pings_attempt1,
 'openssl':{'version':'OpenSSL 3.5.4 30 Sep 2025 (Library: OpenSSL 3.5.4 30 Sep 2025), built from source on both VMs',
            'tarball':'github.com/openssl/openssl/releases openssl-3.5.4.tar.gz','pqa_build':bl(os.path.join(L,'build_pqa.log')),'pqb_build':bl(os.path.join(L,'build_pqb.log')),
            'configure':'./Configure --prefix=/opt/ossl35 --libdir=lib no-tests no-docs; make -j2; make install_sw',
            'note':'install_sw installs no openssl.cnf; certificate made with -config <source>/apps/openssl.cnf'},
 'probe':{'source':'raw.githubusercontent.com/glassgotlazy/pq-tls-flight-geometry/main/testbed/hs.c','sha256':sha(os.path.join(A,'hs.c'))},
 'clienthello_check':rd(os.path.join(A,'chlen_check.csv')),
 'capture':{'file':'vm_A/capture_default.pcap (tcpdump on A test0 egress, one default handshake, R=50 p=0)',
            'result':'PASS: ClientHello left A as two packets, TCP payload 1448 (seq 0:1448) + 45 (seq 1448:1493); www.example.com in one packet',
            'data_packets':[l for l in rd(os.path.join(A,'capture_default.txt')) if not l.endswith('length 0')]},
 'acceptance':{'attempt1':rd(os.path.join(L,'acceptance_attempt1.txt')),'attempt2_retry':rd(os.path.join(L,'acceptance_attempt2.txt')),
               'retry_conditions':rd(os.path.join(L,'retry_conditions.txt')),'baseline_used':'attempt 2 (retry)'},
 'windows_changes':'power-mode overlay set to Best performance for the retry, then reset (was unset; now 00000000-0000-0000-0000-000000000000 = Balanced); wsl --shutdown',
}
json.dump(m,open(os.path.join(L,'meta.json'),'w'),indent=1); print('meta.json written,',len(json.dumps(m)),'bytes')
