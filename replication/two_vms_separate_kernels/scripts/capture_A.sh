#!/bin/bash
# Step 4: one default handshake at R=50 p=0; capture client->server data on test0 egress (after netem).
set -euo pipefail
D=/home/ubuntu/ph; export LD_LIBRARY_PATH=/opt/ossl35/lib
bash $D/netem_A.sh 50 0 > $D/out/capture_qdisc.txt
timeout 6 tcpdump -i test0 -Q out -nn -U -w $D/out/capture_default.pcap 'tcp and dst host 192.168.77.2 and dst port 4505' 2>$D/out/capture_tcpdump.log & T=$!
sleep 1
ip netns exec cli $D/hs 192.168.77.2 4505 default www.example.com 1 0 "capture;cfg=d" > $D/out/capture_handshake.csv
wait $T || true
tcpdump -nn -r $D/out/capture_default.pcap 2>/dev/null > $D/out/capture_default.txt
echo "--- all client->server packets on test0 egress"; cat $D/out/capture_default.txt
echo "--- data packets (TCP payload > 0)"; grep -vE 'length 0$' $D/out/capture_default.txt || true
echo "--- SNI www.example.com present in packet #:"; tcpdump -nn -A -r $D/out/capture_default.pcap 2>/dev/null | grep -c 'www.example.com' || true
cut -d, -f1,7,9,10,12,20 $D/out/capture_handshake.csv
