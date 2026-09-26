#!/bin/sh
# Consumer test for shmux 1.0.3 — run the packaged binary as a tool user.
# usage: sh test_shmux.sh <bindir> <ncurses-package-root> <tmpdir>
set -e

BINDIR="$1"
TERM_ROOT="$2"
SPOOL="$3"

SHMUX="$BINDIR/shmux"
TERMINFO_DIR="$TERM_ROOT/share/terminfo"

test -x "$SHMUX" || { echo "FAIL: $SHMUX not executable"; exit 1; }
test -d "$TERMINFO_DIR" || { echo "FAIL: terminfo db missing at $TERMINFO_DIR"; exit 1; }

export TERM=xterm
export TERMINFO="$TERMINFO_DIR"

OUT="$SPOOL/shmux-test-out.txt"

# 1. parallel fan-out round trip: run echo on 3 local sh: targets
"$SHMUX" -bsQtc 'echo hello-$SHMUX_TARGET' sh:t1 sh:t2 sh:t3 > "$OUT" 2>&1
for t in t1 t2 t3; do
    grep -q "^hello-$t\$" "$OUT" || { echo "FAIL: missing hello-$t in:"; cat "$OUT"; exit 1; }
done
echo "PASS 1/3: parallel fan-out echoed on 3 local targets"

# 2. summary accounting: 2 targets processed
#    (format is "%d target%s processed in ..." -- src/target.c:732, line starts with the count)
"$SHMUX" -r sh -S all -stc 'true' sh:ta sh:tb > "$OUT" 2>&1
grep -q "2 targets processed" "$OUT" || { echo "FAIL: summary not found in:"; cat "$OUT"; exit 1; }
echo "PASS 2/3: summary reports 2 targets processed"

# 3. exit status propagation: target exits 7 -> reported by shmux
"$SHMUX" -r sh -stc 'exit 7' sh:tx > "$OUT" 2>&1 || true
grep -q "exited with status 7" "$OUT" || { echo "FAIL: exit status not reported in:"; cat "$OUT"; exit 1; }
echo "PASS 3/3: target exit status 7 propagated"

echo "ALL 3/3 CONSUMER ASSERTIONS PASSED"
