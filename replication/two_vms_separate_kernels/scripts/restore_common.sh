# shared: restore sysctls + test0 offloads from orig file $O, then write after-state and diff
restore_from_orig() {
  local O=$1
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do
    v=$(grep "^sysctl.net.ipv4.$k=" $O | cut -d= -f2-); sysctl -q -w net.ipv4.$k="$v"; done
  declare -A map=([tcp-segmentation-offload]=tso [generic-segmentation-offload]=gso [generic-receive-offload]=gro [large-receive-offload]=lro)
  for f in "${!map[@]}"; do v=$(grep "^ethtool.test0.$f=" $O | cut -d= -f2); ethtool -K test0 ${map[$f]} $v; done
}
snapshot() {
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "sysctl.net.ipv4.$k=$(cat /proc/sys/net/ipv4/$k)"; done
  for f in tcp-segmentation-offload generic-segmentation-offload generic-receive-offload large-receive-offload; do echo "ethtool.test0.$f=$(ethtool -k test0 | awk -v f="$f:" '$1==f{print $2}')"; done
  echo "tc.test0=$(tc qdisc show dev test0 | tr '\n' '|')"; echo "routes=$(ip route | tr '\n' '|')"
}
