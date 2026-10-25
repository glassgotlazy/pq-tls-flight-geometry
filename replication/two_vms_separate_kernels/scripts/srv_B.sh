#!/bin/bash
# Host B: certificate + six servers (split out of setup_B.sh; install_sw ships no openssl.cnf,
# so req uses the default config from the 3.5.4 source tree).
set -euo pipefail
D=/home/ubuntu/ph; cd $D; export LD_LIBRARY_PATH=/opt/ossl35/lib
/opt/ossl35/bin/openssl req -config /home/ubuntu/build/openssl-3.5.4/apps/openssl.cnf -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 \
  -nodes -days 30 -subj /CN=www.example.com -addext subjectAltName=DNS:www.example.com -keyout ec.key -out ec.crt
/opt/ossl35/bin/openssl x509 -in ec.crt -noout -subject -ext subjectAltName -text | grep -E 'subject=|DNS:|Public Key Algorithm|NIST CURVE'
for p in 4501 4502 4503 4504 4505 4506; do
  setsid nohup /opt/ossl35/bin/openssl s_server -accept $p -cert ec.crt -key ec.key -www -quiet \
    -groups X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:secp256r1 > out/srv_$p.log 2>&1 < /dev/null &
done
sleep 1
{ echo "servers=$(pgrep -c -f '^/opt/ossl35/bin/openssl s_server')"; ethtool -k test0 | grep -E '^(tcp-segmentation|generic-segmentation|generic-receive|large-receive)-offload'
  for k in tcp_congestion_control tcp_early_retrans tcp_recovery tcp_timestamps tcp_sack ip_forward; do echo "$k=$(cat /proc/sys/net/ipv4/$k)"; done
  echo "route: $(ip route get 10.77.0.2 | head -1)"; } | tee out/settings_B.txt
