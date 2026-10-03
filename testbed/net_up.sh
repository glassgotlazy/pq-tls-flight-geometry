#!/bin/bash
# build two namespaces joined by imp.py
ip netns del cli 2>/dev/null; ip netns del srv 2>/dev/null; pkill -f imp.py; sleep 0.5
ip netns add cli; ip netns add srv
echo '{"delay_ms":0}' > /tmp/imp.json
setsid nohup python3 /home/claude/pqtls/imp.py > /tmp/imp.log 2>&1 < /dev/null &
sleep 1
ip link set tunC netns cli; ip link set tunS netns srv
MTU=${1:-1500}
ip -n cli addr add 10.9.0.1/24 dev tunC; ip -n cli link set tunC mtu $MTU up; ip -n cli link set lo up
ip -n srv addr add 10.9.0.2/24 dev tunS; ip -n srv link set tunS mtu $MTU up; ip -n srv link set lo up
for ns in cli srv; do ip netns exec $ns ethtool -K $( [ $ns = cli ] && echo tunC || echo tunS ) gso off tso off 2>/dev/null; done
ip netns exec cli ping -c 2 -W 2 10.9.0.2 | tail -1
