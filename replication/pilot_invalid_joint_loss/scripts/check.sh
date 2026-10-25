#!/bin/bash
. /etc/os-release; echo "distro: $PRETTY_NAME"
for k in tcp_congestion_control tcp_available_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack tcp_rmem tcp_wmem; do echo "$k = $(cat /proc/sys/net/ipv4/$k)"; done
for t in tc ip ethtool gcc make perl curl wget python3 unzip; do printf "%s: " "$t"; command -v "$t" || echo MISSING; done
python3 -c 'import numpy; print("numpy", numpy.__version__)' 2>&1 | tail -1
ls -d /opt/ossl35 2>/dev/null && /opt/ossl35/bin/openssl version 2>/dev/null || echo "/opt/ossl35 absent"
echo "system openssl: $(openssl version 2>/dev/null)"
df -h /opt | tail -1
