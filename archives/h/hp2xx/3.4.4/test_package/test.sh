#!/bin/sh
set -eu

hp2xx --version 2>&1 | grep -F "V 3.4.4" >/dev/null

cat > smoke.hp <<'EOF'
IN;
SP1;
PU;PA0,0;
PD1000,0,1000,1000,0,1000,0,0;
EOF

hp2xx -q -m svg -f smoke.svg smoke.hp
test -s smoke.svg
grep -F "<svg" smoke.svg >/dev/null
grep -F "<path" smoke.svg >/dev/null
