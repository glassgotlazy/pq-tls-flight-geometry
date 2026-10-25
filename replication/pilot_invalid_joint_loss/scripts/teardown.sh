#!/bin/bash
. "$(dirname "$0")/common.sh"
pkill -f 's_server -accept 450' ; pkill -f "$W/hs " ; sleep 1
ip netns del nsA; ip netns del nsB
grep -q 'netem_loaded_before=0' $OUT/orig_state.txt && modprobe -r sch_netem
rm -rf $SRV
{ echo "date_utc=$(date -u +%FT%TZ)"
  echo "netns_after=$(ip netns list | tr '\n' ' ')"; echo "veth_left=$(ip -o link show type veth | wc -l)"
  echo "netem_loaded_after=$(lsmod | grep -c '^sch_netem')"; echo "servers_left=$(pgrep -fc 's_server -accept 450')"
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack; do echo "rootns.$k=$(cat /proc/sys/net/ipv4/$k)"; done
} | tee $OUT/after_teardown.txt
