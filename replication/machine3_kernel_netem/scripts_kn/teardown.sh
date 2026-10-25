#!/bin/bash
. "$(dirname "$0")/common.sh"
pkill -f 's_server -accept 450'; pkill -f "$W/hs "; sleep 1
for n in nsA nsR nsB; do ip netns del $n; done
rm -rf $SRV; sleep 3
modprobe -r sch_netem || { sleep 5; modprobe -r sch_netem; }
{ echo "date_utc=$(date -u +%FT%TZ)"; echo "netns_after=$(ip netns list | tr '\n' ' ')"; echo "veth_left=$(ip -o link show type veth | wc -l)"
  echo "netem_loaded_after=$(lsmod | grep -c '^sch_netem')"; echo "servers_left=$(pgrep -fc 's_server -accept 450')"
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "rootns.$k=$(cat /proc/sys/net/ipv4/$k)"; done
} | tee $OUT/after_teardown.txt
echo "--- orig (root ns) ---"; grep rootns $OUT/orig_state.txt
