#!/bin/bash
set -e
D="$(dirname "$0")"
bash $D/cell.sh TH-wslns 20 0 150
bash $D/cell.sh TH-wslns 20 0.05 1000
bash $D/cell.sh TH-wslns 50 0 150
bash $D/cell.sh TH-wslns 50 0.05 1000
echo ALL_DONE
