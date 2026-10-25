#!/bin/bash
set -uo pipefail
. /home/ubuntu/ph/restore_common.sh; D=/home/ubuntu/ph; O=$D/out/orig_B.txt
pkill -f '^/opt/ossl35/bin/openssl s_server'; sleep 1
ip route del 10.77.0.0/24 via 192.168.77.1 dev test0
restore_from_orig $O
{ snapshot; echo "servers_left=$(pgrep -c -f '^/opt/ossl35/bin/openssl s_server')"; } > $D/out/after_B.txt
echo "--- differences orig_B vs after_B:"; diff <(grep -v '^date_utc' $O) <(grep -v '^servers_left' $D/out/after_B.txt) && echo "none"
grep servers_left $D/out/after_B.txt
