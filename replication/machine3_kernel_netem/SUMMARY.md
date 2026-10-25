# Pass B with kernel netem on a router namespace (pass=KN): single-host stand-in

**This is not a two-host replication.** The setup was three network namespaces inside one WSL2 VM (kernel 6.6.87.2-microsoft-standard-WSL2):
client nsA, router nsR and server nsB, joined by veth pairs. netem ran only on the router:
- vRb (toward the server): delay R/2 and 5% loss
- vRa (toward the client): delay R/2 and no loss

GSO, TSO and GRO were off on all four veth ends. The client and server interfaces had no qdisc (noqueue).
The first run (`pass=TH-wslns`, netem on the client's own egress) is kept unchanged in `run1_TH-wslns/`.

## Check 2: the ClientHello crosses netem as two packets (passed)
One default handshake was captured on the router with an AF_PACKET sniffer (`scripts_kn/sniff.py`; tcpdump was not installed).
The ClientHello was seen at two points: arriving on vRa, i.e. what netem on vRb receives, and leaving vRb, after netem.
At both points it was two packets: TCP payload **1448** bytes (IP length 1500, TLS record header `16 03 01 05 d0`, SNI www.example.com present)
followed by **45** bytes at the next sequence number. See `out/capture_vRa_in.txt` and `out/capture_vRb_out.txt`.

## Check 3: d cluster geometry (initially withheld as partly met; later judged passed by the requester)
| | R=20 | R=50 | Expected | Met? |
|---|---|---|---|---|
| d head cluster | 88 @ **30.4 ms** | 93 @ **68.7 ms** | ≈1.25R = 25 / 63 ms | **No**: about +5.5 ms at both RTTs (1.52R, 1.37R) |
| d tail cluster | 108 @ **246.9 ms** | 96 @ **318.6 ms** | R + T_RTO = 240 / 300 ms | Close at R=20; +6% at R=50 (inside the ±12% window) |
| d stalls at T_RTO | 2 | 0 | almost none | Yes |

These head and tail positions match the paper's own TUN-forwarder pass-B data at R=20 and R=50 (head 30 / 68 ms, tail 246 / 310 ms,
from `analysis/big.py` on `e2big.csv`). So the measurement agrees with the paper; what disagrees is the 1.25R head prediction.
At R=20 the RTO window (202–238 ms) and the tail window (211–269 ms) overlap, so the one-segment "tail" counts are the same handshakes as their RTO counts.

## Results (p = 0.05, client-to-server loss only, rto_min default)
| Setup | R | Stalled two/one seg (%) | Ratio [95% CI] | perm p | head/tail cluster medians (ms) |
|---|---|---|---|---|---|
| KN p=0.05 | 20 | 10.8 / 5.8 | 1.19 [0.97, 1.45] | 0.0485 | d 30.4/246.9; x+h1 0.0/222.8 |
| KN p=0.05 | 50 | 10.3 / 5.1 | 1.58 [1.27, 1.94] | 0.0001 | d 68.7/318.6; x+h1 106.0/274.3 |

The rows are copied exactly from `analysis_output.txt`. The ratio is reported because the requester judged check 3 as passed:
the ~5.5 ms head offset is a constant that is also present in the paper's own data.
- `x+h1 0.0` at R=20 means the head cluster is empty, not a median of 0 ms.
- At R=20 the 95% CI includes 1 while the permutation p is 0.0485. That effect is marginal.
- At R=50, perm p = 0.0001 is the floor for 10,000 permutations (1/10,001), so read it as p ≤ 1e-4.

The one-sided Fisher test on stall counts (d vs pooled x+h1) gives p = 5.7e-12 at R=20 and 2.4e-13 at R=50.
Stalled d handshakes retransmit 1.10–1.16 segments on average (`stall_hist.txt`). The first run's figure was 1.96, so losses are now per packet.
The one-segment configs stall at T_RTO: 222.8 ms (model 220) and about 250 ms (model 250).
n = 2000 per config per cell, and 0 of 13,800 rows were dropped (ok=0). Every cell's ping RTT matched R (`out/ping_*.txt`).
The TcpExt counter deltas on nsA are in `analysis_output.txt`; they are all zero in the p=0 cells.

## Deviations from the plan
1. Namespaces in one WSL2 VM, not two physical hosts. Baseline RTT through the router was 0.073 ms average over 50 pings.
2. netem ran on a router namespace rather than on each host's egress, as requested for this rerun.
3. Probe: `testbed/hs.c` (hs2.c unavailable). Analysis: `ana_wsl.py`, adapted from `analysis/big.py` with unchanged definitions; B = 10,000; Fisher test and p90 added.
4. OpenSSL 3.5.4 was a pre-existing install at /opt/ossl35. It was not rebuilt, and the SHA-256 was not verified.
5. The capture used a Python AF_PACKET sniffer instead of tcpdump, as you chose.
6. The optional rto_min (THD) test was not run.
7. During setup a hung script was stopped and the WSL VM restarted. Everything was rebuilt from scratch before the capture and the cells.
8. Teardown removed all namespaces, veths, servers and the certificate, and unloaded `sch_netem`. The root-namespace sysctls are unchanged (`out/after_teardown.txt`).
