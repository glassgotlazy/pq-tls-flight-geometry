#!/bin/bash
# Host B (pqb): record originals, offloads off on test0, route to cli subnet, cert, six servers.
set -euo pipefail
D=/home/ubuntu/ph; mkdir -p $D/out; O=$D/out/orig_B.txt
[ -e $O ] && { echo "orig_B.txt exists (setup already ran?)"; exit 1; }
{ echo "date_utc=$(date -u +%FT%TZ)"
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "sysctl.net.ipv4.$k=$(cat /proc/sys/net/ipv4/$k)"; done
  for f in tcp-segmentation-offload generic-segmentation-offload generic-receive-offload large-receive-offload; do echo "ethtool.test0.$f=$(ethtool -k test0 | awk -v f="$f:" '$1==f{print $2}')"; done
  echo "tc.test0=$(tc qdisc show dev test0 | tr '\n' '|')"; echo "routes=$(ip route | tr '\n' '|')"
} > $O
sysctl -q -w net.ipv4.tcp_congestion_control=cubic net.ipv4.tcp_timestamps=1 net.ipv4.tcp_sack=1
ethtool -K test0 gso off tso off gro off lro off
ip route add 10.77.0.0/24 via 192.168.77.1 dev test0
bash /home/ubuntu/ph/srv_B.sh   # cert + servers (see srv_B.sh)
