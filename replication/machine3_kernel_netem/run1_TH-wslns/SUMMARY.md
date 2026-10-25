# Pass B with kernel netem: single-host stand-in (WSL2 namespaces)

**This is not a two-host replication.** The client (nsA) and the servers (nsB) ran in two network namespaces inside one WSL2 VM
(kernel 6.6.87.2-microsoft-standard-WSL2) and were joined by a veth pair. netem was placed on each veth's egress.
Label: `pass=TH-wslns`.

## Results (p = 0.05, client-to-server loss only, rto_min default)

| Setup | R | Stalled two/one seg (%) | Ratio [95% CI] | perm p | head/tail cluster medians (ms) |
|---|---|---|---|---|---|
| TH-wslns (netem, veth) | 20 | 5.5 / 5.1 | 0.72 [0.54, 0.92] | 0.9950 | d 20.4/237.7; x+h1 none/223.2 |
| TH-wslns (netem, veth) | 50 | 5.6 / 6.3 | 0.73 [0.57, 0.93] | 0.9945 | d 105.1/273.9; x+h1 105.2/273.2 |
| paper pass B (TUN forwarder), for reference | 20 | 10.9 / 5.6 | 1.34 [1.09, 1.63] | 0.0030 | from big.py output |
| paper pass B (TUN forwarder), for reference | 50 | 10.5 / 5.9 | 1.22 [1.00, 1.50] | 0.0280 | from big.py output |

The one-sided Fisher tests on stall counts (d vs pooled x+h1) give p = 0.332 at R=20 and p = 0.863 at R=50.
Per-config details, the cluster counts and the netstat deltas are in `analysis_output.txt`.
Stall counts: n = 2000 per config per cell, and 0 rows were dropped (ok=0) out of 13,800. No probe iterations were lost.

## Validity problem: two-segment (d) results are not comparable
- d's stall rate matches the one-segment rate (about p) instead of being about 2p as in the paper.
- Stalled d handshakes retransmit about **2** segments on average (`stall_hist.txt`). In the paper's data, d stalls are mostly single retransmissions (`paper_retrans_cmp.txt`).
- d has almost no head cluster (5 and 8 handshakes, compared with 91–108 in the paper).

Conclusion: in this setup, netem dropped both segments of d's ClientHello **together**. The most likely cause is that TCP hands
the qdisc a 2-MSS GSO packet and the kernel segments it only after the qdisc, even with `gso off` on the device.
This is inferred from the data and has not been confirmed with a packet capture. A first diagnostic (`out/diag_gso.txt`) appeared
to rule it out, but that test cannot distinguish the two cases: qdisc packet counters count the segments inside a GSO packet.
**The ratio and the d stall rate above are artefacts and should not be cited as findings.**
The one-segment configs (x, h1) do look valid. Their stalls land on the timer model: RTO cluster at 223 ms (model 220) and 250 ms (model 250).
At R=20 the RTO and tail windows overlap (T_RTO = 220, R + T_RTO = 240), so those counts include the same handshakes twice.

The same problem would affect a real two-host run with loss applied by netem on A's egress. The loss has to be applied after segmentation,
for example by a forwarding hop with GRO off and netem on its egress.

## Deviations from the plan
1. The hosts were namespaces in one WSL2 VM, not two physical hosts. Baseline RTT was 0.075 ms over 50 pings.
2. The probe was `testbed/hs.c` from the repository (`hs2.c` was unavailable). It has the same command line and the same ch_len column. The ClientHello lengths check out: 254 / 1440 / 1488.
3. `ana2.py` was unavailable. The analysis is `ana_wsl.py`, adapted from `analysis/big.py` with unchanged definitions. B is set to 10,000 for the bootstrap and permutation tests, and a one-sided Fisher test and p90 were added.
4. OpenSSL 3.5.4 was a pre-existing install at /opt/ossl35. It was not rebuilt, and the tarball SHA-256 was not verified in this session.
5. The optional rto_min (THD) test was not run.
6. Sysctls were set inside the test namespaces only; their defaults already matched the plan. The root-namespace values were unchanged before and after the run.
   Teardown removed the namespaces, the veth pair, the servers and the certificate, and unloaded `sch_netem` (it was not loaded before the run).
