#!/bin/bash
# usage: cell.sh PASS R_ms p N   (netem on router: vRb -> server delay R/2 + loss p; vRa -> client delay R/2)
set -euo pipefail
. "$(dirname "$0")/common.sh"
PASS=$1; R=$2; P=$3; N=$4; TAG="${PASS}_R${R}_p${P}"
HALF=$(awk -v r=$R 'BEGIN{printf "%g", r/2}')
LOSS=""; [ "$P" != "0" ] && LOSS="loss $(awk -v p=$P 'BEGIN{printf "%g%%", p*100}')"
ip netns exec nsR tc qdisc replace dev vRb root netem delay ${HALF}ms $LOSS limit 10000
ip netns exec nsR tc qdisc replace dev vRa root netem delay ${HALF}ms limit 10000
{ echo "# $TAG $(date -u +%FT%TZ)"; ip netns exec nsR tc qdisc show dev vRb; ip netns exec nsR tc qdisc show dev vRa
  echo "nsA vA: $(ip netns exec nsA tc qdisc show dev vA)"; echo "nsB vB: $(ip netns exec nsB tc qdisc show dev vB)"
  ip netns exec nsA ping -c 20 -i 0.05 -q $B_IP | tail -2; } > $OUT/ping_$TAG.txt
ip netns exec nsA grep TcpExt /proc/net/netstat > $OUT/ctr_${TAG}_before.txt
pids=""
for c in "x X25519 4501 4502" "h1 X25519MLKEM768:X25519 4503 4504" "d default 4505 4506"; do set -- $c
  for s in 0 1; do port=$([ $s = 0 ] && echo $3 || echo $4)
    ip netns exec nsA $W/hs $B_IP $port $2 www.example.com $N 0 "pass=$PASS;rtt=$R;p=$P;cfg=$1;stream=$s" \
      > $OUT/raw_${TAG}_$1_s$s.csv 2> $OUT/err_${TAG}_$1_s$s.txt & pids="$pids $!"
  done
done
wait $pids
ip netns exec nsA grep TcpExt /proc/net/netstat > $OUT/ctr_${TAG}_after.txt
ip netns exec nsR tc -s qdisc show dev vRb > $OUT/qdisc_stats_${TAG}_vRb.txt
echo "$TAG done $(date -u +%T) rows=$(cat $OUT/raw_${TAG}_*.csv | grep -vc '^label')"
