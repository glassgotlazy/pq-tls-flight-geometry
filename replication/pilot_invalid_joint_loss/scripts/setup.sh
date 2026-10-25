#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/common.sh"
mkdir -p $OUT
# --- record original state (root namespace) ---
{
 echo "date_utc=$(date -u +%FT%TZ)"
 echo "kernel=$(uname -r)"; echo "cpus=$(nproc)"
 echo "netem_loaded_before=$(lsmod | grep -c '^sch_netem' || true)"
 echo "netns_before=$(ip netns list | tr '\n' ' ')"
 for k in tcp_congestion_control tcp_available_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack; do echo "rootns.$k=$(cat /proc/sys/net/ipv4/$k)"; done
} > $OUT/orig_state.txt
ip netns list | grep -qE '^ns(A|B)\b' && { echo "nsA/nsB already exist, aborting"; exit 1; }
modprobe sch_netem
# --- namespaces + veth ---
ip netns add nsA; ip netns add nsB
ip link add $IFA type veth peer name $IFB
ip link set $IFA netns nsA; ip link set $IFB netns nsB
ip -n nsA addr add $A_IP/24 dev $IFA; ip -n nsB addr add $B_IP/24 dev $IFB
for n in nsA nsB; do ip -n $n link set lo up; done
ip -n nsA link set $IFA up; ip -n nsB link set $IFB up
# --- per-namespace settings: record defaults, then set ---
for n in nsA nsB; do
 for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack; do echo "$n.default.$k=$(ip netns exec $n cat /proc/sys/net/ipv4/$k)"; done >> $OUT/orig_state.txt
 ip netns exec $n sysctl -q -w net.ipv4.tcp_congestion_control=cubic net.ipv4.tcp_timestamps=1 net.ipv4.tcp_sack=1
done
ip netns exec nsA ethtool -K $IFA gso off tso off gro off
ip netns exec nsB ethtool -K $IFB gso off tso off gro off
# --- build probe ---
gcc $W/src/hs.c -O2 -o $W/hs -I/opt/ossl35/include -L/opt/ossl35/lib -lssl -lcrypto
# --- cert ---
mkdir -p $SRV
$OSSL req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 30 -subj /CN=www.example.com \
  -addext subjectAltName=DNS:www.example.com -keyout $SRV/ec.key -out $SRV/ec.crt 2>/dev/null
# --- servers ---
for port in 4501 4502 4503 4504 4505 4506; do
 ip netns exec nsB nohup $OSSL s_server -accept $port -cert $SRV/ec.crt -key $SRV/ec.key -www -quiet \
   -groups X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1 > $OUT/srv_$port.log 2>&1 &
done
sleep 1
echo "servers: $(pgrep -fc 's_server -accept 450')"
echo "--- ns settings ---"
for n in nsA nsB; do for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack; do echo "$n.$k=$(ip netns exec $n cat /proc/sys/net/ipv4/$k)"; done; done
ip netns exec nsA ethtool -k $IFA | grep -E '^(generic-segmentation|tcp-segmentation|generic-receive)-offload'
ip netns exec nsB ethtool -k $IFB | grep -E '^(generic-segmentation|tcp-segmentation|generic-receive)-offload'
echo "--- baseline ping x50 ---"
ip netns exec nsA ping -c 50 -i 0.02 -q $B_IP | tail -2 | tee $OUT/baseline_ping.txt
echo "probe openssl: $(LD_LIBRARY_PATH=/opt/ossl35/lib $OSSL version)"
ldd $W/hs | grep -E 'libssl|libcrypto'
