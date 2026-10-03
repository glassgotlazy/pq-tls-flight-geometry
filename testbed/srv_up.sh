#!/bin/bash
pkill -f "s_server" ; sleep 0.3
G=${1:-X25519MLKEM768:X25519:SecP256r1MLKEM768:MLKEM768:MLKEM1024:SecP384r1MLKEM1024:secp256r1}
CERT=${2:-ec}
EXTRA=${3:-}
setsid -f ip netns exec srv env LD_LIBRARY_PATH=/opt/ossl35/lib /opt/ossl35/bin/openssl s_server -accept 4433 -cert /home/claude/pqtls/$CERT.crt -key /home/claude/pqtls/$CERT.key -www -quiet -groups $G $EXTRA > /tmp/srv.log 2>&1 < /dev/null
sleep 1
