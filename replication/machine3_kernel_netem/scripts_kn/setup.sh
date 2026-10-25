#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/common.sh"
mkdir -p $OUT
{ echo "date_utc=$(date -u +%FT%TZ)"; echo "kernel=$(uname -r)"; echo "cpus=$(nproc)"
  echo "netem_loaded_before=$(lsmod | grep -c '^sch_netem' || true)"; echo "netns_before=$(ip netns list | tr '\n' ' ')"
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "rootns.$k=$(cat /proc/sys/net/ipv4/$k)"; done
} > $OUT/orig_state.txt
[ -z "$(ip netns list)" ] || { echo "namespaces already exist, aborting"; exit 1; }
modprobe sch_netem
for n in nsA nsR nsB; do ip netns add $n; ip -n $n link set lo up; done
ip link add vA type veth peer name vRa; ip link set vA netns nsA; ip link set vRa netns nsR
ip link add vB type veth peer name vRb; ip link set vB netns nsB; ip link set vRb netns nsR
ip -n nsA addr add $A_IP/24 dev vA;  ip -n nsR addr add $RA_IP/24 dev vRa
ip -n nsB addr add $B_IP/24 dev vB;  ip -n nsR addr add $RB_IP/24 dev vRb
for p in "nsA vA" "nsR vRa" "nsR vRb" "nsB vB"; do set -- $p; ip -n $1 link set $2 up; ip netns exec $1 ethtool -K $2 gso off tso off gro off; done
ip -n nsA route add default via $RA_IP; ip -n nsB route add default via $RB_IP
ip netns exec nsR sysctl -q -w net.ipv4.ip_forward=1
for n in nsA nsR nsB; do
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack; do echo "$n.default.$k=$(ip netns exec $n cat /proc/sys/net/ipv4/$k)"; done >> $OUT/orig_state.txt
  ip netns exec $n sysctl -q -w net.ipv4.tcp_congestion_control=cubic net.ipv4.tcp_timestamps=1 net.ipv4.tcp_sack=1
done
gcc $W/src/hs.c -O2 -o $W/hs -I/opt/ossl35/include -L/opt/ossl35/lib -lssl -lcrypto
mkdir -p $SRV
$OSSL req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 30 -subj /CN=www.example.com \
  -addext subjectAltName=DNS:www.example.com -keyout $SRV/ec.key -out $SRV/ec.crt 2>/dev/null
for port in 4501 4502 4503 4504 4505 4506; do
  ip netns exec nsB nohup $OSSL s_server -accept $port -cert $SRV/ec.crt -key $SRV/ec.key -www -quiet \
    -groups X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1 > $OUT/srv_$port.log 2>&1 &
done
sleep 1; echo "servers: $(pgrep -fc 's_server -accept 450')"
{ for p in "nsA vA" "nsR vRa" "nsR vRb" "nsB vB"; do set -- $p; echo "== $1 $2"; ip netns exec $1 ethtool -k $2 | grep -E '^(generic-segmentation|tcp-segmentation|generic-receive)-offload'; done
  for n in nsA nsR nsB; do for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "$n.$k=$(ip netns exec $n cat /proc/sys/net/ipv4/$k)"; done; done
  for p in "nsA vA" "nsB vB"; do set -- $p; echo "$1 $2 qdisc: $(ip netns exec $1 tc qdisc show dev $2)"; done
} | tee $OUT/settings.txt
echo "--- baseline ping x50 (A->B through router, no netem) ---"
ip netns exec nsA ping -c 50 -i 0.02 -q $B_IP | tail -2 | tee $OUT/baseline_ping.txt
