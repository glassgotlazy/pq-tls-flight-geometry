W=<WORKDIR>/run2_KN
OUT=$W/out; SC=$(dirname "$0")
A_IP=10.77.1.1; RA_IP=10.77.1.254; RB_IP=10.77.2.254; B_IP=10.77.2.2
export LD_LIBRARY_PATH=/opt/ossl35/lib
OSSL=/opt/ossl35/bin/openssl; SRV=/root/tlsrv
