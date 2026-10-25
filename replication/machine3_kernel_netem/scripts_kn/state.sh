#!/bin/bash
echo "uptime: $(cut -d' ' -f1 /proc/uptime)s"; echo "netns files: $(ls /run/netns 2>/dev/null | tr '\n' ' ')"
echo "netns list: $(ip netns list | tr '\n' ' ')"; echo "veths: $(ip -o link show type veth | wc -l)"
echo "netem loaded: $(lsmod | grep -c '^sch_netem')"; echo "servers: $(pgrep -fc 's_server -accept 450')"
for n in $(ip netns list | cut -d' ' -f1); do ip netns del $n 2>/dev/null && echo "deleted stale $n"; done
rm -rf /root/tlsrv
