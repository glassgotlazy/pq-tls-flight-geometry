# Flight Geometry of Post-Quantum TLS 1.3 over TCP: reproducibility package

Regenerates every number in the paper. Tested on Linux 6.18 (x86-64), OpenSSL 3.5.4 built from source, Python 3.12.

## Requirements
- Root, network namespaces, /dev/net/tun (tc-netem is NOT required; imp.py replaces it)
- OpenSSL 3.5.4 installed at /opt/ossl35 (`./Configure --prefix=/opt/ossl35 && make && make install_sw`)
- `gcc hs.c -o hs -I/opt/ossl35/include -L/opt/ossl35/lib -lssl -lcrypto`
- Python 3; `pip install curl_cffi` for the browser-fingerprint measurement
- `pip install numpy` for analysis/big.py and analysis/final.py

## Layout
| Path | Purpose | Paper |
|---|---|---|
| testbed/net_up.sh | builds `cli`/`srv` namespaces joined by imp.py (TUN pair, GSO/TSO off) | V-A |
| testbed/imp.py | userspace impairment engine: one-way delay, Bernoulli / Gilbert-Elliott loss, per-direction | V-A |
| testbed/hs.c | probe client: timestamps, ClientHello/ServerHello parsing, TCP_INFO retransmits | V-B |
| testbed/e1.sh | E1 geometry captures (tcpdump) | VI-A, Table IV |
| testbed/e2final.py | E2 passes A, B, C | VI-B, Tables VI-VIII |
| testbed/e2big.py | E2 pass B at 2,000 handshakes per configuration, parallel streams | VI-B |
| geometry/ch.py, matrix.py | OpenSSL s_client/s_server ClientHello size and resumption matrix | IV-A, VI-C |
| geometry/browsers.py | browser-fingerprint ClientHellos via curl_cffi | Table V |
| analysis/big.py, big_output.txt | 2,000-handshake pass B: clusters, bootstrap CIs, permutation tests (exact output committed) | Tables VI-VII |
| analysis/final.py, final_output.txt, stalls.py | passes A, B (300), C (exact output committed) | Table VIII |
| data/ | raw CSV/JSON from the runs reported in the paper | all |

## Run order
```
sudo ./testbed/net_up.sh 1500
sudo ./testbed/srv_up.sh
sudo ./testbed/e1.sh                      # Table IV
sudo python3 testbed/e2big.py             # Tables VI-VII (about 35 min)
python3 analysis/big.py                   # Tables VI-VII
python3 analysis/final.py                 # Table VIII
```
`python3 analysis/big.py` reproduces Tables VI-VII exactly from `data/e2big.csv`; its output is committed as
`analysis/big_output.txt` (`python3 analysis/big.py | diff - analysis/big_output.txt` prints nothing).
Each (R, p) cell uses its own random generator, `numpy.random.default_rng(1000*R + round(100*p))`, with
10,000 bootstrap resamples and 10,000 permutations, so a cell's CIs and p-values do not depend on which other cells exist.
`python3 analysis/final.py` reproduces Table VIII (and the 300-handshake pass B ratios) exactly; its output is
committed as `analysis/final_output.txt` (`python3 analysis/final.py | diff - analysis/final_output.txt` prints nothing).
Each cell uses its own generator, `numpy.random.default_rng(zlib.crc32("<pass>|<R>|<model>|<p>|<group>"))`,
with 10,000 bootstrap resamples.

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
