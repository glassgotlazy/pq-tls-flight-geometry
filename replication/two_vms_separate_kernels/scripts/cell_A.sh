#!/bin/bash
# usage: cell_A.sh R p N  (runs on pqa as root; six probes in cli; label pass=PH)
set -euo pipefail
D=/home/ubuntu/ph; OUT=$D/out; export LD_LIBRARY_PATH=/opt/ossl35/lib
R=$1; P=$2; N=$3; TAG="PH_R${R}_p${P}"; B=192.168.77.2
{ echo "# $TAG $(date -u +%FT%TZ)"; bash $D/netem_A.sh $R $P; ip netns exec cli ping -c 20 -i 0.05 -q $B | tail -2; } > $OUT/ping_$TAG.txt
ip netns exec cli grep TcpExt /proc/net/netstat > $OUT/ctr_${TAG}_before.txt
pids=""
for c in "x X25519 4501 4502" "h1 X25519MLKEM768:X25519 4503 4504" "d default 4505 4506"; do set -- $c
  for s in 0 1; do port=$([ $s = 0 ] && echo $3 || echo $4)
    ip netns exec cli $D/hs $B $port $2 www.example.com $N 0 "pass=PH;rtt=$R;p=$P;cfg=$1;stream=$s" \
      > $OUT/raw_${TAG}_$1_s$s.csv 2> $OUT/err_${TAG}_$1_s$s.txt & pids="$pids $!"
  done
done
wait $pids
ip netns exec cli grep TcpExt /proc/net/netstat > $OUT/ctr_${TAG}_after.txt
tc -s qdisc show dev test0 > $OUT/qdisc_stats_${TAG}_test0.txt
echo "$TAG done $(date -u +%T) rows=$(cat $OUT/raw_${TAG}_*.csv | grep -vc '^label')"
