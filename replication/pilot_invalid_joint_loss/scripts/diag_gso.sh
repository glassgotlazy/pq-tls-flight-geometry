#!/bin/bash
# Diagnostic: does netem on vA see one skb per TCP segment, or GSO super-packets?
. "$(dirname "$0")/common.sh"
modprobe sch_netem
ip netns add nsA; ip netns add nsB
ip link add $IFA type veth peer name $IFB; ip link set $IFA netns nsA; ip link set $IFB netns nsB
ip -n nsA addr add $A_IP/24 dev $IFA; ip -n nsB addr add $B_IP/24 dev $IFB
for n in nsA nsB; do ip -n $n link set lo up; done; ip -n nsA link set $IFA up; ip -n nsB link set $IFB up
ip netns exec nsA ethtool -K $IFA gso off tso off gro off; ip netns exec nsB ethtool -K $IFB gso off tso off gro off
mkdir -p $SRV; $OSSL req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 1 -subj /CN=www.example.com -keyout $SRV/ec.key -out $SRV/ec.crt 2>/dev/null
ip netns exec nsB $OSSL s_server -accept 4501 -cert $SRV/ec.crt -key $SRV/ec.key -www -quiet -groups X25519MLKEM768:X25519 >/dev/null 2>&1 &
sleep 1
for cfg in X25519 default; do
  ip netns exec nsA tc qdisc replace dev $IFA root netem delay 1ms limit 10000
  rx0=$(ip netns exec nsB cat /sys/class/net/$IFB/statistics/rx_packets)
  ip netns exec nsA $W/hs $B_IP 4501 $cfg www.example.com 50 0 diag > /dev/null
  rx1=$(ip netns exec nsB cat /sys/class/net/$IFB/statistics/rx_packets)
  q=$(ip netns exec nsA tc -s qdisc show dev $IFA | grep -oP 'Sent \d+ bytes \K\d+(?= pkt)')
  qb=$(ip netns exec nsA tc -s qdisc show dev $IFA | grep -oP 'Sent \K\d+(?= bytes)')
  echo "cfg=$cfg 50 handshakes: netem_dequeued_pkts=$q netem_bytes=$qb vB_rx_pkts=$((rx1-rx0)) avg_bytes_per_netem_pkt=$((qb/q))"
done
ip netns exec nsA ethtool -k $IFA | grep -E '^(generic-segmentation|tx-tcp-segmentation)'
pkill -f 's_server -accept 4501'; sleep 1; ip netns del nsA; ip netns del nsB; rm -rf $SRV
sleep 3; modprobe -r sch_netem && echo "sch_netem unloaded" ; echo "netem_loaded=$(lsmod | grep -c '^sch_netem') netns=$(ip netns list | wc -l)"
