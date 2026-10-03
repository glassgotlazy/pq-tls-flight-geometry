#!/bin/bash
# run_loss.sh OUT N : loss sweep. Server must be running in srv ns.
OUT=$1; N=${2:-100}; HS=/home/claude/pqtls/hs; export LD_LIBRARY_PATH=/opt/ossl35/lib
echo -n > $OUT
first=1
for rtt in 50 200; do
 for spec in "bernoulli 0" "bernoulli 0.01" "bernoulli 0.02" "bernoulli 0.05" "bernoulli 0.10" "ge 0.05" "ge 0.10"; do
  set -- $spec; model=$1; p=$2
  if [ $model = ge ]; then pbg=0.5; pgb=$(python3 -c "print($p*$pbg/(1-$p))"); json="{\"delay_ms\":$rtt,\"model\":\"ge\",\"p_gb\":$pgb,\"p_bg\":$pbg,\"seed\":$RANDOM}";
  else json="{\"delay_ms\":$rtt,\"model\":\"bernoulli\",\"p\":$p,\"seed\":$RANDOM}"; fi
  echo "$json" > /tmp/imp.json; sleep 1
  for g in X25519 X25519MLKEM768:X25519 default; do
   lab="rtt=$rtt;model=$model;p=$p"
   ip netns exec cli $HS 10.9.0.2 4433 $g www.example.com $N 0 "$lab" > /tmp/part.csv 2>/dev/null
   if [ $first = 1 ]; then cat /tmp/part.csv > $OUT; first=0; else tail -n +2 /tmp/part.csv >> $OUT; fi
  done
 done
done
echo FINISHED >> /tmp/loss_status
