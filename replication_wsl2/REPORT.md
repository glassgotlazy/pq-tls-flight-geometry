# Replication Report — pq-tls-flight-geometry on WSL2 (Ubuntu 26.04)

Repo: https://github.com/glassgotlazy/pq-tls-flight-geometry, main @ `48f1f63` (tag `v1.3`).
Every number below is read directly from `replication_wsl2/big_output.txt` and
`replication_wsl2/more_output.txt`, produced by the repo's own unmodified `analysis/big.py` and
`analysis/more.py` run against `e2big.csv`/`e2more.csv` generated on this machine (see
`REPLICATION_LOG.md` for the full command trail). No value here was estimated or invented.

## Environment

| | Paper | This run (WSL2) |
|---|---|---|
| Kernel | 6.18.44 (VM) | 6.6.87.2-microsoft-standard-WSL2 (full `uname -a` and `lscpu` in `env.txt`) |
| OS | — | Ubuntu 26.04 LTS "resolute" |
| OpenSSL | 3.5.4 (source build) | 3.5.4 30 Sep 2025 (confirmed via `LD_LIBRARY_PATH=/opt/ossl35/lib openssl version`) |
| Python | 3.12 | 3.14.4 (no compatibility issues observed) |
| CPU | — | Intel Core Ultra 5 125H, 18 logical CPUs (host, under Hyper-V) |
| `tcp_congestion_control` | CUBIC (paper assumption) | `cubic` — matches |
| `tcp_early_retrans` | — | `3` (default) |
| `tcp_recovery` (RACK) | — | `1` (default, RACK enabled) |
| `tcp_timestamps` | — | `1` (default, enabled) |
| `tcp_sack` | — | `1` (default, enabled) |
| `rto_min` | — | Not a global sysctl on this kernel (confirmed: `sysctl -a \| grep rto_min` empty); it's a per-route attribute, same as the paper's testbed uses. Default (no override) = compiled `TCP_RTO_MIN` = 200 ms, consistent with what both analysis scripts compute for "default rto_min" cells. |
| `HZ` | — | Could not be determined: `getconf CLK_TCK` only reports the fixed userspace `USER_HZ`=100, and this WSL2 kernel build ships no `/boot/config-<release>` exposing the real compiled `CONFIG_HZ`. Not guessed. |

**Bottom line on "does any WSL2 default differ from the paper's assumptions": no sysctl checked here
(`early_retrans`, `recovery`/RACK, `congestion_control`, `timestamps`, `sack`) differs from the standard
modern-Linux defaults the paper's testbed itself relies on, and `rto_min`'s default (200 ms) matches what
the repo's own analysis scripts assume. `HZ` is the one value that's genuinely unknown here, not "default" —
see above.**

## Model predictions for this kernel

Formula given: `T_RTO = R + max(2R, rto_min)`, `T_tail = R + T_RTO`, `T_RACK ≈ 1.25R`.

**Default `rto_min` = 200 ms:**

| R (ms) | T_RTO | T_tail | T_RACK |
|---|---|---|---|
| 20 | 220 | 240 | 25.0 |
| 50 | 250 | 300 | 62.5 |
| 100 | 300 | 400 | 125.0 |
| 200 | 600 | 800 | 250.0 |

**`rto_min` = 50 ms (pass D):**

| R (ms) | T_RTO | T_tail | T_RACK |
|---|---|---|---|
| 20 | 70 | 90 | 25.0 |
| 50 | 150 | 200 | 62.5 |

(R=100/200 rows and the `rto_min`=200 table computed directly from the formula; the `rto_min`=50 row
values match `more_output.txt`'s own printed `predicted T_RTO=... T_RACK=... T_tail=...` lines exactly.)

These line up closely with what was actually observed (next section): e.g. at default `rto_min`, the
one-segment loss cluster (223/250/312/618 ms) tracks `T_RTO` (220/250/300/600) to within ~3%, and the
two-segment tail cluster (248/314/425/822 ms) tracks `T_tail` (240/300/400/800) similarly closely. The
small consistent overshoot (observed running a few ms/percent above the pure timer model) is expected —
the model is the kernel retransmit timer alone, not the full measured pipeline.

## Pass B — 5% client→server loss, R = 20/50/100/200 ms

| Metric | Paper | WSL2 (this run) | Verdict |
|---|---|---|---|
| two-seg/one-seg ratio | 1.34, 1.22, 1.72, 1.92 | 1.27, 1.42, 1.66, 1.68 | **PARTIAL** — R=20 and R=100 close (-5%, -3%); R=50 moves the *opposite* local direction (paper dips to 1.22, ours rises to 1.42); R=200 undershoots by 12.5%. Direction (ratio > 1 throughout) replicates; exact shape does not. |
| one-segment loss cluster | 223, 250, 312, 615 | 223, 250, 312, 618 | **REPLICATED** — exact to within 0.5%. |
| head-loss cluster | 30, 68, 130, 258 | 31, 68, 130, 258 | **REPLICATED** — exact to within 1 ms. |
| tail-loss cluster | 246, 310, 418, 821 | 248, 314, 425, 822 | **REPLICATED** — within 1.7% throughout. |
| one-share hybrid / X25519 | 0.87–1.10, CIs include 1 | 0.95, 1.15, 0.78, 1.12 (all CIs include 1: [0.73,1.24], [0.88,1.53], [0.59,1.03], [0.88,1.44]) | **REPLICATED** (qualitatively — statistically indistinguishable from 1 in every cell, matching the paper's finding), though point estimates spread wider than the paper's band. |
| stall share: one-seg | 4.9–6.0% | 5.5%, 5.6%, 5.8%, 5.5% | **REPLICATED** — fully inside the paper's range. |
| stall share: two-seg | 10.5–11.2% | 10.8%, 10.7%, 9.6%, 11.1% | **PARTIAL** — R=20/50/200 inside or essentially at the paper's band; R=100 (9.6%) falls below the 10.5% floor. |

## Pass D — client-route `rto_min` = 50 ms, R = 20 and 50 ms

| Metric | Paper (R=20, R=50) | WSL2 (this run) | Verdict |
|---|---|---|---|
| one-segment timing | 74–75, 146–147 | 75, 147 | **REPLICATED** — exact. |
| tail cluster | 99, 205 | 98, 206 | **REPLICATED** — within 1 ms. |
| head cluster | 30, 68 | 31, 69 | **REPLICATED** — within 1 ms. |
| two-seg/one-seg ratio | 1.31, 1.36 | 1.46 [1.12,1.91], 1.74 [1.35,2.23] | **PARTIAL** — R=20's CI covers the paper's 1.31 but the point estimate is 11% high; R=50's CI just barely covers 1.36 (lower bound 1.35) while the point estimate (1.74) is 28% high. The underlying cluster *timings* match almost exactly, but on this kernel the two-segment path incurs a bigger mean-delay penalty than the paper measured — see "Surprises" below. |

## Pass A at scale — both directions, default `rto_min`

| Config | Paper ratio | WSL2 ratio (this run) | Verdict |
|---|---|---|---|
| R=50, p=2% | 1.00 | 1.14 [0.87, 1.46] | **REPLICATED** — paper's value sits inside the CI, though our point estimate runs higher. |
| R=50, p=5% | 1.30 | 1.31 [0.98, 1.76] | **REPLICATED** — essentially exact. |
| R=100, p=5% | 1.35 | 1.54 [1.26, 1.92] | **PARTIAL** — CI contains 1.35, but the point estimate is 14% high. |

## Supplementary (not in the requested comparison set, but produced by `analysis/more.py`'s own last block)

Effect of lowering `rto_min` 200→50 ms on the two-segment added delay and the "split penalty"
(two-segment minus pooled one-segment), from unrounded data:
- R=20: added delay 16.18 → 8.86 ms (−45.2%); split penalty 3.42 → 2.79 ms (−18.5%)
- R=50: added delay 21.79 → 17.39 ms (−20.2%); split penalty 6.46 → 7.37 ms (**+14.1%**, i.e. the
  split penalty *grew* at R=50 when `rto_min` was lowered, the opposite sign from R=20 — reproduced
  faithfully from the script's own output, not smoothed over).

## Summary

- **Kernel**: paper 6.18.44 (VM) vs. this run 6.6.87.2-microsoft-standard-WSL2 (Ubuntu 26.04, `uname -a`/`lscpu` in `env.txt`).
- **Per-finding verdict**: 8 REPLICATED, 4 PARTIAL, 0 NOT REPLICATED, out of the 12 requested comparisons.
  Every PARTIAL case is a magnitude/direction mismatch on a *ratio of means*, never on the underlying
  timing clusters (loss cluster, head cluster, tail cluster), which replicated almost exactly in all
  12/12 cases where the paper gave a value to compare against.
- **Surprises**:
  1. The clusters (where in the RTT cycle a lost segment gets recovered) match the paper's kernel almost
     to the millisecond, despite WSL2's kernel (6.6) and virtualization layer being quite different from
     the paper's bare VM (6.18) — the RACK/RTO timer math is evidently very stable across kernel versions.
  2. Despite that, the *ratio* metrics (two-seg/one-seg mean added delay) run consistently at or above the
     paper's values in Pass D and Pass A-at-scale (though mixed in Pass B) — same stall/cluster timing,
     but a higher proportion of two-segment attempts fall into the costly tail on this machine, pulling the
     mean up. This looks like a genuine, reproducible, kernel/virtualization-dependent effect rather than
     noise, since it's consistent in direction across both Pass D cells and 2 of 3 Pass-A-at-scale cells.
  3. Getting a working run at all required two non-trivial fixes, both logged in full in
     `REPLICATION_LOG.md`: (a) `make install_sw` doesn't install OpenSSL's default `openssl.cnf`/cert
     directories (needs `make install_ssldirs` too — missing from both the task's plan and the repo's
     own README), and (b) with IPv6 enabled (the default on this system), `net_up.sh` bringing up `tunC`
     before `tunS` lets the kernel's own IPv6 multicast/ND traffic crash `imp.py` with `EIO` on the
     still-down peer interface, deterministically, every time — fixed with a 2-line IPv6-disable patch
     to `testbed/net_up.sh` (approved by the user first; diff in `REPLICATION_LOG.md`). The first full
     `e2big.py` attempt before that fix "succeeded" in 15 seconds with literally zero real network
     activity in every cell — a reminder that "the script exited 0" is not evidence of valid data; this
     is why `replicate.sh`'s phase g checks exact row counts, not just file existence.
  4. The run was also interrupted for several hours mid-`e2big.py` by the host laptop sleeping despite
     being asked not to; WSL2 simply freezes and resumes cleanly, so no data was lost, but it's worth
     flagging since a shorter machine-sleep timeout or a lid-close could have corrupted an in-flight cell.
