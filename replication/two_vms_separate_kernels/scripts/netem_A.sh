#!/bin/bash
# usage: netem_A.sh R_ms p   -> c2s on test0 (delay R/2 [loss p]), s2c on vroot (delay R/2)
set -euo pipefail
HALF=$(awk -v r=$1 'BEGIN{printf "%g", r/2}'); LOSS=""; [ "$2" != "0" ] && LOSS="loss $(awk -v p=$2 'BEGIN{printf "%g%%", p*100}')"
tc qdisc replace dev test0 root netem delay ${HALF}ms $LOSS limit 10000
tc qdisc replace dev vroot root netem delay ${HALF}ms limit 10000
tc qdisc show dev test0; tc qdisc show dev vroot
