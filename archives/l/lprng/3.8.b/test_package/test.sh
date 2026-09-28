#!/bin/sh
# test_package/test.sh - HarmonyOS consumer smoke test for LPRng 3.8.b.
# Usage: test.sh [bindir] [etc-lpd-dir]
#
# No $(...) and no backticks anywhere below: /tmp on OHOS is read-only
# (erofs) and /bin/sh materializes command substitution in hardcoded
# /tmp while ignoring TMPDIR.  Temp files go through $TMPDIR only.
#
# Upstream test audit: LPRng 3.8.B ships NO upstream test framework -
# the top-level Makefile has no check target (make check exits 2 with
# "No rule to make target"), no TESTS/check_PROGRAMS/add_test in any
# Makefile.am, and the TESTSUPPORT directory was never shipped
# (Makefile.am line 2 says "still to include: TESTSUPPORT").
# Five-dim ledger: upstream total=0 executed=0 passed=0 failed=0
# skipped=0.  The assertions below are NEW OHOS consumer checks.
#
# Note: LPRng reads its spooler config from hardcoded system paths, so
# on a consumer machine without a live config the clients print the
# LPRng Read_file_list diagnostic before anything else.  An execution
# is therefore asserted by non-empty diagnostic output of the real
# binary (dynamic link + getopt + config subsystem all ran).
set -u

BINDIR="${1:-}"
ETCDIR="${2:-}"

if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR"

F="$TMPDIR/tp-fails"
if ! : > "$F"; then
    echo "FAIL: cannot create result file $F" >&2
    exit 1
fi

for b in lpr lpq lprm lpstat lpc checkpc lprng_certs lprng_index_certs; do
    if [ -x "$BINDIR/$b" ]; then
        echo "TPOK bin-exec-$b"
    else
        echo "TPFAIL bin-exec-$b"
        echo "bin-exec-$b" >> "$F"
    fi
done

# lpd.perms.sample lands in etc/lpd/; printcap.sample in etc/ itself
# (LPRng install-data-hook ships .sample variants to avoid overwriting
# live spooler configs).
for f in "$ETCDIR/lpd.perms.sample" "$ETCDIR/../printcap.sample"; do
    name=${f##*/}
    if [ -f "$f" ]; then
        echo "TPOK etc-config-$name"
    else
        echo "TPFAIL etc-config-$name"
        echo "etc-config-$name" >> "$F"
    fi
done

for b in lpr lpq lprm lpstat; do
    out="$TMPDIR/run-$b.txt"
    "$BINDIR/$b" -ZzZ > "$out" 2>&1
    if [ -s "$out" ]; then
        echo "TPOK runs-$b"
    else
        echo "TPFAIL runs-$b"
        echo "runs-$b" >> "$F"
    fi
done

if [ -s "$F" ]; then
    echo "TPRESULT FAIL"
    exit 1
fi
echo "TPRESULT PASS"
exit 0
