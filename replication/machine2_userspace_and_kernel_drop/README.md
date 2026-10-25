# Replication additions (second machine, kernel-side loss, resumed-handshake timing)

Run on a separate cloud VM: 2 vCPUs, Linux 6.18.44, OpenSSL 3.5.4 built from source (data/meta.json).
Kernel netem was unavailable (CONFIG_NET_SCH_NETEM not set), so delay comes from imp.py as on the first testbed.
CUBIC was set host-wide before the namespaces were created.

- hs2.c: testbed/hs.c plus an optional 9th argument (groups for the resumed handshake)
- imp.py: testbed/imp.py with the config path taken from $IMP_CFG
- run2.py: phases B2 (pass B, R=20/50 ms), K (R=50 ms, nftables random drop at server ingress; imp.py adds delay only), S (resumption timing, R=50 ms, 5% c2s loss)
- ana2.py: same definitions as analysis/big.py -> ana2_output.txt
- penalty_ci.py: bootstrap CIs of the split penalty (passes B, D) vs Eq. (3) -> penalty_ci_output.txt
- data/: b2.csv, k.csv, s.csv, *_ctr.jsonl, meta.json, ana2.json

- make_figures.py: builds every figure in the paper. Usage: python3 make_figures.py <repo_root> <out_dir>.
  It reads the repository's data/ folder; the replication ratios in Fig. 5b for the third machine
  and the two-VM run are written into the script as constants copied from
  replication/machine3_kernel_netem and replication/two_vms_separate_kernels.
