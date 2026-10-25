#!/bin/bash
. "$(dirname "$0")/common.sh"
echo "servers alive: $(pgrep -fc 's_server -accept 450')"
for c in "x X25519 4501" "h1 X25519MLKEM768:X25519 4503" "d default 4505"; do set -- $c
 ip netns exec nsA $W/hs $B_IP $3 $2 www.example.com 3 0 "check;cfg=$1" | tail -n +2
done | tee $OUT/chlen_check.csv | cut -d, -f1,7,9,10,11,12,15,20
