echo "host=$(hostname) kernel=$(uname -r) cpus=$(nproc)"
echo "CONFIG_HZ: $(grep -E '^CONFIG_HZ=' /boot/config-$(uname -r))"
echo "clocksource: $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource)"
for k in tcp_congestion_control tcp_available_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "$k=$(cat /proc/sys/net/ipv4/$k)"; done
echo "test0: $(ip -br link show test0)  mtu=$(cat /sys/class/net/test0/mtu) driver=$(ethtool -i test0 | awk '/^driver/{print $2}')"
ethtool -k test0 | grep -E '^(tcp-segmentation-offload|generic-segmentation-offload|generic-receive-offload|large-receive-offload):'
echo "test0 qdisc: $(tc qdisc show dev test0)"
echo "routes: $(ip route | tr '\n' ';')"
