#!/bin/sh
# Consumer test for the installed loki 2.4.7.4 programs.
# Exercises the four installed binaries on synthetic data (no network, no
# external dataset); the upstream statistical suite is run in build().
set -eu

B="${LOKI_BINDIR:?LOKI_BINDIR must point at the installed bin dir}"
[ -d "$B" ] || { echo "FAIL- missing bindir $B"; exit 1; }

WORK="${TMPDIR:-${HOME:?HOME not set}/tmp}/loki-conftest-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

checks=0
fails=0
ck() {
    checks=$((checks + 1))
    if printf '%s\n' "$3" | grep -qF -- "$2"; then
        echo "ok  - $1"
    else
        echo "FAIL- $1: expected '$2'"
        fails=$((fails + 1))
    fi
}

# 1. all four programs installed and executable
for p in loki prep qavg hist; do
    checks=$((checks + 1))
    if [ -x "$B/$p" ]; then echo "ok  - $p installed"; else
        echo "FAIL- $p missing/not executable"; fails=$((fails + 1)); fi
done

# 2. loki version banner (-v) + argument check
out=$("$B/loki" -v 2>&1 || true)
ck "loki version banner" "loki 2.4.7_4" "$out"
out=$("$B/loki" 2>&1 || true)
ck "loki requires a parameter file" "No parameter file specified" "$out"

# 3. prep requires a control file
out=$("$B/prep" 2>&1 || true)
ck "prep requires a control file" "No control file specified" "$out"

# 4. hist usage + real histogram on a real file
out=$("$B/hist" -h 2>&1 || true)
ck "hist usage" "usage: hist" "$out"
printf '1\n2\n3\n4\n5\n' > "$WORK/h.dat"
out=$("$B/hist" "$WORK/h.dat" 2>&1 || true)
ck "hist computes a histogram" "0.200000" "$out"

# 5. qavg real run on synthetic columns
printf '1 2\n3 4\n5 6\n' > "$WORK/q.dat"
out=$("$B/qavg" "$WORK/q.dat" 2>&1 || true)
ck "qavg column 1 mean" "Col 1 - Mean = 3" "$out"
ck "qavg column 2 mean" "Col 2 - Mean = 4" "$out"

echo "LOKI_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
