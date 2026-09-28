#!/bin/sh
# klick-0.12.2 packaged-tool smoke test.
#
# klick is a JACK metronome: a real metronome session cannot run headless on
# OHOS/CI (no jackd), so the pass condition is layered (readings recorded
# per layer):
#
#   Layer 1 (loading): the binary exists and is executable — its full
#           runtime shared-library closure resolves, otherwise the dynamic
#           loader dies with exit 127 before main() runs.
#   Layer 2a (version): klick -V prints the "klick 0.12.2" banner to
#           stdout and exits 0 (Options::parse, before any JACK activity).
#   Layer 2b (usage): klick -h prints the "Usage:" block and exits 0
#           (same early path; proves iostream + option parsing run).
#
# Session layer (JACK server / audio backend) is declared not runnable
# headless — no jackd on the OHOS device/CI; recorded in notes.md.
#
# NOTE 1: OHOS /system/bin/sh (toybox) lacks command substitution, so
# captures are done through a file instead.
#
# NOTE 2 (L1e discipline): every file this test writes goes into a private
# output directory given as the second argument (the caller passes an
# absolute path under the Conan test build folder). The framework's negative
# reference round runs the very same test_package right after the positive
# one, so nothing may ever be written relative to the current directory: a
# leftover there is a dirty file inside the archive directory and gets
# picked up by a directory-wide git add. The directory name is suffixed with
# the shell pid, so the two rounds can not clobber each other, and it is
# removed on the success path.
#
# Usage: test_klick.sh <path-to-bin-dir> [path-to-output-dir]

set -u

BIN_DIR="$1"
OUT_BASE="${2:-$PWD/klick-smoke-out}"
OUT="$OUT_BASE.$$"
ERRFILE="$OUT/klick-smoke.err"

# Always remove the private output directory, on the pass path as well as on
# every failure path (the readings themselves are echoed to stderr below, so
# they survive in the caller log). This is what keeps both the positive and
# the negative reference round free of leftovers inside the archive tree.
trap 'rm -rf "$OUT"' EXIT

if [ ! -x "$BIN_DIR/klick" ]; then
    echo "FAIL: klick not found or not executable in $BIN_DIR" >&2
    exit 1
fi

mkdir -p "$OUT" || { echo "FAIL: cannot create output dir $OUT" >&2; exit 1; }

# Layer 2a: -V version banner (exit 0 upstream).
"$BIN_DIR/klick" -V >"$ERRFILE" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "FAIL: klick -V returned $rc (127 = shared-library load failure)" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi
if ! grep -q "klick 0.12.2" "$ERRFILE"; then
    echo "FAIL: klick -V did not print the version banner" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi

# Layer 2b: -h usage block (exit 0 upstream).
"$BIN_DIR/klick" -h >"$ERRFILE" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "FAIL: klick -h returned $rc (127 = shared-library load failure)" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi
if ! grep -q "Usage:" "$ERRFILE"; then
    echo "FAIL: klick -h did not print the usage block" >&2
    head -n 5 "$ERRFILE" >&2
    exit 1
fi

echo "KLICK_SMOKE_PASS version=1 usage=1 out_dir_removed=1"
exit 0
