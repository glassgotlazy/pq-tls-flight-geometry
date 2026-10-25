# Pass PH: two VMs with kernel netem on a forwarding hop

**Not two physical machines.** Host A (`pqa`) and host B (`pqb`) are two VMware Workstation VMs on one Windows 11 Home laptop,
each with its own Ubuntu 24.04 kernel (6.8.0-147, CONFIG_HZ=1000), 2 vCPUs and 1.5 GB RAM. They are joined by a private VMware LAN segment (`test0`).
SSH used a separate NAT NIC (`mgmt0`). The client ran in namespace `cli` on A, and A's root namespace forwarded to B.
netem ran only on A: `test0` carried c2s traffic (delay 25 ms, loss 5%) and `vroot` carried s2c traffic (delay 25 ms).

## Result (R = 50 ms, p = 0.05, client-to-server loss only, rto_min default)

| Setup | R | Stalled two/one seg (%) | Ratio [95% CI] | perm p | default head/tail medians (ms) |
|---|---|---|---|---|---|
| PH (2 VMs, one laptop) | 50 | 11.0 / 5.8 | 1.43 [1.19, 1.71] | 0.0003 | 67.3 / 307.8 |

The row is taken from `analysis_output.txt`. In that file the last column also lists the pooled x+h1 cluster medians (58.9 / 277.1).
The one-sided Fisher test on stall counts (d vs pooled x+h1) gives p = 1.23e-12.
Rows: 6,900 read, **0 dropped** (ok=0). n = 2000 per config in the lossy cell and 300 per config in the p=0 baseline.

### Validity check (passed)
| Criterion | Measured | Expected |
|---|---|---|
| d head cluster | 88 stalls, median 67.3 ms | about 68–71 ms (0.7 ms below the band) |
| d tail cluster | 113 stalls, median 307.8 ms | about 300–320 ms |
| d stalls at T_RTO (250 ms) | 1 | almost none |
| x / h1 stalls near T_RTO | RTO cluster 89 at 257.6 ms / 95 at 257.2 ms | near 250 ms |

Stalled d handshakes retransmit 1.07 segments on average (`stall_hist.txt`), so losses hit individual packets.

TcpExt deltas, measured in `cli` (the analysis output's "nsA" label is inherited from the earlier script):
TCPLossProbes 326, TCPLossProbeRecovery 277, TCPTimeouts 387, TCPSackRecovery 405 in the p=0.05 cell, and all zero in the p=0 cell.

## Gating checks
- **Split capture (Step 4): passed.** tcpdump on A's `test0` egress shows the default ClientHello as 1,448 + 45 bytes of TCP payload (`vm_A/capture_default.*`).
- **ClientHello lengths:** 254 / 1440 / 1488 (`vm_A/chlen_check.csv`).
- **Acceptance check (p=0, R=50, t_tls − 50 ms; thresholds: median ≤ 3, IQR ≤ 2, p99 ≤ 10):**

| Attempt | x median / IQR / p99 | h1 median / IQR / p99 | d median / IQR / p99 | Result |
|---|---|---|---|---|
| 1 | 2.719 / 1.383 / 16.426 | 3.113 / 1.704 / 14.762 | 3.294 / 2.146 / 13.585 | FAIL |
| 2 (retry, used as the baseline) | 2.086 / 0.865 / 6.854 | 2.338 / 0.999 / 9.472 | 2.339 / 0.780 / 7.690 | PASS |

The retry ran under these conditions: WSL shut down, Windows power mode Best performance, on AC power.
Chrome and Rainmeter were still open, by your choice. The VMware process priority could not be raised (it needs admin rights), so it was left at normal.

## Deviations from the plan
1. The two "hosts" are VMs on one physical machine. They share the CPU, memory and hypervisor, and that is not two physical machines.
2. Step 1's LAN RTT rule failed: 50 idle pings averaged 1.967 ms, with a maximum of 23.1 ms. At your instruction it was replaced by the p=0 acceptance check above.
   A 10 ms-interval diagnostic gave an average of 0.561 ms and a p99 of 2.03 ms.
3. LRO was also turned off on both test NICs, as you added.
4. `make install_sw` installs no `openssl.cnf`, so B's certificate was created with `-config <source>/apps/openssl.cnf`. The build itself followed the plan exactly, and the tarball SHA-256 matched on both VMs.
5. Only R = 50 ms was run (R = 20 ms skipped as instructed). The optional rto_min test was not run.
6. Windows changes made for the retry were `wsl --shutdown` and the power mode set to Best performance. The power mode was reset afterwards; it was unset before and is now the Balanced GUID.

## Restore
Both VMs were checked against their recorded originals and show **no differences**: sysctls, `test0` offloads, default mq/fq_codel qdisc and routes (`vm_A/after_A.txt`, `vm_B/after_B.txt`).
The namespace, veth, netem qdiscs, forwarding setting and the route on B were removed, `sch_netem` was unloaded and the servers were stopped.
The VMs, the image and the SSH key (`~/.ssh/id_ed25519_pqvm`) are kept, as you asked.
