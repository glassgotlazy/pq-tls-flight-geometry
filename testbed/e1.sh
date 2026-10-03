#!/bin/bash
cd /home/claude/pqtls; export LD_LIBRARY_PATH=/opt/ossl35/lib
OUT=e1.csv; echo -n > $OUT; first=1
for mtu in 1500 1400 1280; do
 ip -n cli link set tunC mtu $mtu; ip -n srv link set tunS mtu $mtu
 for cfg in X25519 secp256r1 X25519MLKEM768:X25519 default SecP256r1MLKEM768 MLKEM768 MLKEM1024 SecP384r1MLKEM1024; do
  for sni in a.io www.example.com shop.verylongsubdomain.example-cdn.net $(python3 -c "print('x'*50+'.example.com')"); do
   timeout 2 ip netns exec cli tcpdump -i tunC -nn -l 'tcp dst port 4433 and tcp[tcpflags] & tcp-push != 0 or (tcp dst port 4433 and len > 100)' > /tmp/cap.txt 2>/dev/null &
   sleep 0.4
   ip netns exec srv ss -ltn | grep -q 4433 || ./srv_up.sh; ip netns exec cli ./hs 10.9.0.2 4433 $cfg $sni 1 0 "mtu=$mtu" > /tmp/p.csv
   sleep 1.5; wait
   # count client data segments before server's first response: crude = data segments to 4433 in first connection with length>0, excluding the final Finished
   segs=$(grep -c "length" /tmp/cap.txt)
   lens=$(grep -o "length [0-9]*" /tmp/cap.txt | awk '{print $2}' | tr '\n' ' ')
   if [ $first = 1 ]; then head -1 /tmp/p.csv | sed 's/$/,mtu,seg_lens/' > $OUT; first=0; fi
   tail -n +2 /tmp/p.csv | sed "s/\$/,$mtu,$lens/" >> $OUT
  done
 done
done
ip -n cli link set tunC mtu 1500; ip -n srv link set tunS mtu 1500
