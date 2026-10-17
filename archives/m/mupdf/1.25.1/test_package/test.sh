#!/bin/sh
# Test: verify mutool binary runs and reports version.
# Invoked by test_package/conanfile.py test() with the packaged mutool's
# absolute path as $1 (E428: absolute path — OHOS conanrun env carries no
# PATH entry for the dependency bindir, bare "mutool" would exit 127).
# POSIX sh: no pipefail; the single assertion uses explicit || handling.
set -eu
if [ $# -lt 1 ]; then
    echo "FAIL: usage: test.sh <abs-path-to-mutool>" >&2
    exit 1
fi
MUTOOL="$1"
"$MUTOOL" -v 2>&1 | grep -q "1.25.1" || { echo "FAIL: mutool not working"; exit 1; }
echo "PASS: mutool reports version 1.25.1"
