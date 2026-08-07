#!/bin/sh
set -eu

cat > sample.abc <<'EOF'
X:1
T:Smoke test
M:4/4
L:1/4
K:C
CDEF|
EOF

abcm2ps -O output.ps sample.abc
test -s output.ps
