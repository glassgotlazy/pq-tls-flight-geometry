W=<WORKDIR>/run
OUT=$W/out
A_IP=10.77.0.1; B_IP=10.77.0.2; IFA=vA; IFB=vB
export LD_LIBRARY_PATH=/opt/ossl35/lib
OSSL=/opt/ossl35/bin/openssl
SRV=/root/tlsrv   # server files on the Linux fs
