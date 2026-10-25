#!/bin/bash
# Host A (pqa): record originals, then build cli namespace + veth, forwarding, offloads off, probe.
set -euo pipefail
D=/home/ubuntu/ph; mkdir -p $D/out; O=$D/out/orig_A.txt
[ -e $O ] && { echo "orig_A.txt exists (setup already ran?)"; exit 1; }
{ echo "date_utc=$(date -u +%FT%TZ)"
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "sysctl.net.ipv4.$k=$(cat /proc/sys/net/ipv4/$k)"; done
  for f in tcp-segmentation-offload generic-segmentation-offload generic-receive-offload large-receive-offload; do echo "ethtool.test0.$f=$(ethtool -k test0 | awk -v f="$f:" '$1==f{print $2}')"; done
  echo "tc.test0=$(tc qdisc show dev test0 | tr '\n' '|')"
  echo "routes=$(ip route | tr '\n' '|')"; echo "netns=$(ip netns list | tr '\n' ' ')"
  echo "sch_netem_loaded_at_setup=$(lsmod | grep -c '^sch_netem' || true) (loaded by Step 1 check; was 0 before)"
} > $O
sysctl -q -w net.ipv4.tcp_congestion_control=cubic net.ipv4.tcp_timestamps=1 net.ipv4.tcp_sack=1
sysctl -q -w net.ipv4.ip_forward=1
ip netns add cli
ip link add vroot type veth peer name vcli; ip link set vcli netns cli
ip addr add 10.77.0.1/24 dev vroot; ip link set vroot up
ip -n cli addr add 10.77.0.2/24 dev vcli; ip -n cli link set vcli up; ip -n cli link set lo up
ip -n cli route add default via 10.77.0.1
ip netns exec cli sysctl -q -w net.ipv4.tcp_congestion_control=cubic net.ipv4.tcp_timestamps=1 net.ipv4.tcp_sack=1
off() { ethtool -K $2 gso off tso off gro off; ethtool -K $2 lro off 2>/dev/null || echo "$1 $2: lro not changeable ($(ethtool -k $2 | awk '/^large-receive-offload/{print $2,$3}'))"; }
ethtool -K test0 gso off tso off gro off lro off
off root vroot; ip netns exec cli bash -c "$(declare -f off); off cli vcli"
# probe from the repository
curl -fsSL -o $D/hs.c https://raw.githubusercontent.com/glassgotlazy/pq-tls-flight-geometry/main/testbed/hs.c
echo "hs.c sha256 $(sha256sum $D/hs.c | cut -d' ' -f1)"
gcc $D/hs.c -O2 -o $D/hs -I/opt/ossl35/include -L/opt/ossl35/lib -lssl -lcrypto
{ for i in "root test0" "root vroot" "cli vcli"; do set -- $i; echo "== $1 $2"; ip netns exec $1 true 2>/dev/null || true
    if [ $1 = cli ]; then ip netns exec cli ethtool -k $2; else ethtool -k $2; fi | grep -E '^(tcp-segmentation|generic-segmentation|generic-receive|large-receive)-offload'; done
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "root.$k=$(cat /proc/sys/net/ipv4/$k) cli.$k=$(ip netns exec cli cat /proc/sys/net/ipv4/$k)"; done
} | tee $D/out/settings_A.txt
