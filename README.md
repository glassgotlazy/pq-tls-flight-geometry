# Flight Geometry of Post-Quantum TLS 1.3 over TCP: reproducibility package

Regenerates every number in the paper. Tested on Linux 6.18 (x86-64), OpenSSL 3.5.4 built from source, Python 3.12.

## Requirements
- Root, network namespaces, /dev/net/tun (tc-netem is NOT required; imp.py replaces it)
- OpenSSL 3.5.4 installed at /opt/ossl35 (`./Configure --prefix=/opt/ossl35 && make && make install_sw`)
- `gcc hs.c -o hs -I/opt/ossl35/include -L/opt/ossl35/lib -lssl -lcrypto`
- Python 3; `pip install curl_cffi` for the browser-fingerprint measurement
- `pip install numpy` for analysis/big.py, analysis/final.py and analysis/more.py

## Layout
| Path | Purpose | Paper |
|---|---|---|
| testbed/net_up.sh | builds `cli`/`srv` namespaces joined by imp.py (TUN pair, GSO/TSO off) | V-A |
| testbed/imp.py | userspace impairment engine: one-way delay, Bernoulli / Gilbert-Elliott loss, per-direction | V-A |
| testbed/hs.c | probe client: timestamps, ClientHello/ServerHello parsing, TCP_INFO retransmits | V-B |
| testbed/e1.sh | E1 geometry captures (tcpdump) | VI-A, Table IV |
| testbed/e2final.py | E2 passes A, B, C | VI-B, Table IX |
| testbed/e2big.py | E2 pass B at 2,000 handshakes per configuration, parallel streams | VI-B |
| testbed/e2more.py | E2 pass D (client route rto_min 50 ms, 1,000 per configuration) and pass A at scale (loss in both directions, 2,000 per configuration); sets and restores `rto_min` on the client route | VI-B, Tables VIII, X |
| geometry/ch.py, matrix.py | OpenSSL s_client/s_server ClientHello size and resumption matrix | IV-A, VI-C |
| geometry/browsers.py | browser-fingerprint ClientHellos via curl_cffi | Table V |
| analysis/big.py, big_output.txt | 2,000-handshake pass B: clusters, bootstrap CIs, permutation tests (exact output committed) | Tables VI-VII |
| analysis/final.py, final_output.txt, stalls.py | passes A, B (300), C (exact output committed) | Table IX |
| analysis/more.py, more_output.txt | pass D (rto_min causal test) and pass A at scale: clusters, bootstrap CIs, permutation tests (exact output committed) | Tables VIII, X |
| data/ | raw CSV/JSON from the runs reported in the paper | all |

## Run order
```
sudo ./testbed/net_up.sh 1500
sudo ./testbed/srv_up.sh
sudo ./testbed/e1.sh                      # Table IV
sudo python3 testbed/e2big.py             # Tables VI-VII (about 35 min)
python3 analysis/big.py                   # Tables VI-VII
python3 analysis/final.py                 # Table IX
sudo python3 testbed/e2more.py            # passes D and A at scale
python3 analysis/more.py                  # Tables VIII, X
```
`python3 analysis/big.py` reproduces Tables VI-VII exactly from `data/e2big.csv`; its output is committed as
`analysis/big_output.txt` (`python3 analysis/big.py | diff - analysis/big_output.txt` prints nothing).
Each (R, p) cell uses its own random generator, `numpy.random.default_rng(1000*R + round(100*p))`, with
10,000 bootstrap resamples and 10,000 permutations, so a cell's CIs and p-values do not depend on which other cells exist.
`python3 analysis/final.py` reproduces Table IX (and the 300-handshake pass B ratios) exactly; its output is
committed as `analysis/final_output.txt` (`python3 analysis/final.py | diff - analysis/final_output.txt` prints nothing).
Each cell uses its own generator, `numpy.random.default_rng(zlib.crc32("<pass>|<R>|<model>|<p>|<group>"))`,
with 10,000 bootstrap resamples.
`python3 analysis/more.py` reproduces Tables VIII and X exactly from `data/e2more.csv`; its output is committed as
`analysis/more_output.txt` (`python3 analysis/more.py | diff - analysis/more_output.txt` prints nothing). Each cell uses
its own generator, `numpy.random.default_rng(zlib.crc32(<cell key>))`, with 10,000 bootstrap resamples and 10,000
permutations. `data/e2more_ctr.jsonl` holds the client TCP counters per cell.
Its last block reads `data/e2big.csv` as well and prints, from the unrounded data, how much lowering rto_min from 200 to
50 ms reduces the two-segment added delay and the split penalty (paper Sections VI-B and VII).

Kernel timer constants referenced in the paper: net/ipv4/tcp_output.c (tcp_schedule_loss_probe, lines 3063-3079),
net/ipv4/tcp_input.c (tcp_rtt_estimator, lines 1095-1096), include/net/tcp.h (__tcp_set_rto, lines 834-837),
net/ipv4/tcp_recovery.c (tcp_rack_reo_wnd), Linux v6.18.

## Real-browser ClientHello capture (`browsers_real/`)
Replaces the curl_cffi impersonation of `geometry/browsers.py` with real browser builds (paper Table V, upper group).
```
# self-signed ECDSA P-256 certificate for the local server (any OpenSSL)
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout k.pem -out c.pem \
  -days 365 -subj "/CN=www.example.com" -addext "subjectAltName=DNS:www.example.com"
cd browsers_real && cp ../c.pem ../k.pem .
node drive.js edge msedge 5                      # Playwright channel; or pass an executable path
python3 parse.py ../data/browsers_real.csv       # parses raw/*.txt with geometry/ch.py
python3 report.py                                # Table V rows + comparison with data/browsers.json
```
Each run starts a fresh `openssl s_server -www -msg` on port 8443 (OpenSSL 3.5.4) and a fresh browser
profile (`chromium.launch()`), with `--host-resolver-rules=MAP www.example.com 127.0.0.1 --no-proxy-server`.
`raw/` holds the s_server logs of the published run (Microsoft Edge 154.0.4258.53 and the Playwright-bundled
Chromium 141.0.7390.37, Linux 6.18.44, Ubuntu 24.04, headless, 5 connections each).

## Replication runs (Table II of the paper)
| Table II row | Folder | Hardware |
|---|---|---|
| Second machine, R=20 and 50 ms | replication/machine2_userspace_and_kernel_drop (`b2.csv`) | second cloud VM (2 vCPUs, Linux 6.18.44). Kernel netem was not available on this machine (`CONFIG_NET_SCH_NETEM` not set), so delay and loss come from the user-space `imp.py`, as on the first testbed |
| Kernel-side loss, R=50 ms | replication/machine2_userspace_and_kernel_drop (`k.csv`) | same cloud VM: random drop by nftables at the server's ingress; `imp.py` adds the delay only |
| Third machine, netem, R=20 and 50 ms | replication/machine3_kernel_netem | WSL2 on a Windows 11 laptop: one Linux kernel, three network namespaces (client, router, server), kernel tc-netem on the router's egress |
| Two VMs, netem, R=50 ms | replication/two_vms_separate_kernels | two VMware Workstation VMs on one Windows 11 laptop, each with its own Linux 6.8 kernel; kernel tc-netem on the forwarding host A |
| Resumed handshakes (hybrid vs X25519) | replication/machine2_userspace_and_kernel_drop (`s.csv`) | same cloud VM: resumption timing at R=50 ms with 5% client-to-server loss |

Each folder keeps its own `SUMMARY.md` (or README) unchanged from the run, together with `meta.json`, the raw CSVs, the client TCP counters,
the analysis script and that script's complete output.
- **Second machine:** `python3 -I ana2.py <dir>` reproduces `ana2_output.txt` (it needs numpy and scipy).
  Point it at a copy of `data/`, because it rewrites `ana2.json` in the directory it is given.
  `python3 -I penalty_ci.py <repo_root>` reproduces `penalty_ci_output.txt` from the top-level `data/`.
- **Third machine:** the analysis script (`scripts_kn/ana_wsl.py`) expects the raw CSVs and the counter files in one directory.
  Copy `raw/` and `counters/` into one directory and run `python3 scripts_kn/ana_wsl.py <dir> 200`.
  The output matches the committed `analysis_output.txt`.
- **Two VMs:** rebuilt the same way with `scripts/ana_ph.py`. `scripts/accept.py` rebuilds both acceptance tables.
- **Two-VM jitter check:** the planned idle-ping LAN-RTT check failed (mean 1.97 ms against a 1 ms limit).
  It was replaced by a p=0 acceptance check, fixed before the first attempt ran: per configuration, t_tls − R must have a median ≤ 3 ms,
  an IQR ≤ 2 ms and a p99 ≤ 10 ms.
  The first attempt failed the p99 limit and was discarded (not used as the baseline).
  A retry passed and is the baseline. Before it, WSL was shut down and Windows was switched to Best performance mode. Both acceptance tables are in the folder
  (`acceptance_attempt1.txt`, `acceptance_attempt2.txt`, `accept_attempt1/`).
- **Pilot:** `replication/pilot_invalid_joint_loss` is the first WSL pilot (pass TH). It is **invalid** and is kept only for transparency;
  it is not used in the paper. With netem on the sender's own interface, the two ClientHello segments were dropped together.
  The likely cause is that netem saw them as one GSO packet. This is inferred from retransmit counts, not confirmed by a capture;
  see that folder's `SUMMARY.md`.
  `replication/machine3_kernel_netem/run1_TH-wslns/` holds a second copy of the same pilot, also not used.
- **Figures:** `replication/machine2_userspace_and_kernel_drop/make_figures.py` produces Figs. 1 and 3-7 of the paper
  (fig1_timeline, fig3_profiles, fig4_sni, fig5_loss, fig6_clusters, fig7_bidir). Fig. 2, the testbed diagram, is drawn in LaTeX
  in the paper source. The script also writes fig8_resumption, which the current paper no longer uses. Run it as `python3 -I make_figures.py <repo_root> <out_dir>`; it needs numpy, scipy, matplotlib and the Liberation Serif font.
  It reads the repository's `data/` folder.
  The ratio points in Fig. 5b are constants written into the script, not computed when it runs:
  - third machine and two-VM run: copied from `replication/machine3_kernel_netem` and `replication/two_vms_separate_kernels`;
  - machine 1: copied from `analysis/big_output.txt`;
  - machine 2: copied from `ana2_output.txt`.
  All of them match their sources after rounding to two decimals.

## Known issues
- The testbed scripts hard-code `/home/claude/pqtls/` (imp.py, hs, certificates, output files). Create that
  directory or edit the paths. The server certificates `ec.crt`/`ec.key` (and `rsachain.pem` for pass C) are not included.
- `make install_sw` of OpenSSL 3.5.4 puts the libraries in `/opt/ossl35/lib64` on x86-64. The scripts use
  `/opt/ossl35/lib`; add `ln -s lib64 /opt/ossl35/lib`, or the probe will silently load the system libssl.
- `net_up.sh` needs iproute2 and ethtool; if ethtool is missing, GSO/TSO stay on without an error message.
- `data/e2big.csv` covers 10% loss only at RTT 20 ms (9 of the 12 planned cells in `e2big.py`).
- The paper states CUBIC; new network namespaces inherit the host's `net.ipv4.tcp_congestion_control`.

## License
MIT, see `LICENSE`.
