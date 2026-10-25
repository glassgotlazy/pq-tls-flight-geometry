#!/bin/bash
. "$(dirname "$0")/common.sh"
echo "servers alive: $(pgrep -fc 's_server -accept 450')"
ip netns exec nsR tc qdisc replace dev vRb root netem delay 10ms limit 10000
ip netns exec nsR tc qdisc replace dev vRa root netem delay 10ms limit 10000
ip netns exec nsR python3 -I $SC/sniff.py vRa 3 > $OUT/capture_vRa_in.txt & P1=$!
ip netns exec nsR python3 -I $SC/sniff.py vRb 3 > $OUT/capture_vRb_out.txt & P2=$!
sleep 0.7
ip netns exec nsA $W/hs $B_IP 4505 default www.example.com 1 0 "capture;cfg=d" > $OUT/capture_handshake.csv
wait $P1 $P2
ip netns exec nsR tc -s qdisc show dev vRb > $OUT/capture_qdisc_vRb.txt
cut -d, -f1,7,9,10,12,20 $OUT/capture_handshake.csv
for f in capture_vRa_in capture_vRb_out; do echo "=== $f (client->server, payload>0)"; grep '10.77.1.1:[0-9]* > 10.77.2.2' $OUT/$f.txt | grep -v 'tcp_payload=0 '; done
