#!/bin/bash
set -uo pipefail
. /home/ubuntu/ph/restore_common.sh; D=/home/ubuntu/ph; O=$D/out/orig_A.txt
pkill -f "$D/hs " 2>/dev/null
tc qdisc del dev test0 root 2>/dev/null; ip netns del cli 2>/dev/null   # veth pair (and its netem) goes with the namespace
restore_from_orig $O
sleep 1; modprobe -r sch_netem && echo "sch_netem unloaded"
{ snapshot; echo "netns=$(ip netns list | tr '\n' ' ')"; echo "veth_left=$(ip -o link show type veth | wc -l)"; echo "sch_netem_loaded=$(lsmod | grep -c '^sch_netem')"; } > $D/out/after_A.txt
echo "--- differences orig_A vs after_A (date/netem lines expected to differ):"; diff <(grep -vE '^(date_utc|sch_netem|netns)' $O) <(grep -vE '^(date_utc|sch_netem|netns|veth_left)' $D/out/after_A.txt) && echo "none"
cat $D/out/after_A.txt | grep -E 'netns|veth|netem'
