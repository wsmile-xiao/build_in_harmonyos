#!/bin/sh
# Smoke test for the dict package (no sockets, no daemon).
# 1. dict / dictd report their version.
# 2. dictzip -> dictunzip round-trip restores the original bytes.
# 3. dictfmt builds a tiny dictionary; dictd answers a DEFINE query through
#    the upstream-supported `--stdin2stdout` pipe mode (same protocol path
#    the upstream test suite exercises).
set -eu
LC_ALL=C
export LC_ALL

work=$PWD

echo "== versions =="
# Both dict and dictd print their banner and exit 1 by upstream design
# (dict.c/dictd.c: `case 'V': banner(); exit(1);`).  Check the banner text
# instead of the exit code.
dict --version 2>&1 | grep -q "1\.13\.3"
dictd --version 2>&1 | grep -q "1\.13\.3"

echo "== dictzip roundtrip =="
awk 'BEGIN { for (i = 0; i < 5000; ++i) printf "line %d: the quick brown fox jumps\n", i }' > sample.txt
cp sample.txt sample.expected
dictzip -k sample.txt
test -f sample.txt.dz
dictunzip -f sample.txt.dz
cmp sample.expected sample.txt
echo "dictzip roundtrip passed"

echo "== dictfmt + dictd stdin2stdout =="
cat > smoke.txt <<'EOF'
_____

hello
hello definition line
_____

world
world definition line
EOF
# -c5: headwords are preceded by a line of at least 5 "_" (the format of
# smoke.txt below).
dictfmt -c5 --without-time --silent --without-ver smoke < smoke.txt
test -s smoke.dict
test -s smoke.index

cat > smoke.conf <<EOF
database smoke {
   index "$work/smoke.index"
   data  "$work/smoke.dict"
}
EOF

printf 'define smoke hello\nquit\n' > cmds.txt
dictd -c smoke.conf -i --stdin2stdout < cmds.txt > answer.txt
grep -q "definitions retrieved" answer.txt
grep -q "hello definition line" answer.txt
echo "dictd stdin2stdout passed"

echo "SMOKE_OK"
