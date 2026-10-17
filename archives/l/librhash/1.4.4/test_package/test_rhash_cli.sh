#!/bin/sh
# test_rhash_cli.sh — CLI-level smoke test for the packaged rhash binary.
# Assertions ported from upstream tests/test_rhash.sh (RHash v1.4.4).
# Usage: test_rhash_cli.sh <path-to-rhash-binary>
# R25: shell scripts must start with `set -euo pipefail`. All [ ] tests are
# inside if conditions, so set -e is suppressed there and the manual fail
# counter keeps working; pipefail only surfaces real pipeline failures.
set -euo pipefail

RHASH="$1"
fail=0

check_eq() { # label expected actual
    if [ "$3" = "$2" ]; then
        echo "ok   : $1"
    else
        echo "FAIL : $1 — expected '$2', got '$3'"
        fail=$((fail + 1))
    fi
}

check_prefix() { # label expected_prefix actual
    case "$3" in
        "$2"*)
            echo "ok   : $1"
            ;;
        *)
            echo "FAIL : $1 — expected prefix '$2', got '$3'"
            fail=$((fail + 1))
            ;;
    esac
}

# default CRC32 of "abc" (upstream: `rhash --message "abc"` → "(message) 352441C2")
out="$($RHASH --message 'abc' 2>/dev/null | tail -n1)"
check_eq "CRC32(abc)" "(message) 352441C2" "$out"

# MD5 of "abc" (upstream: `rhash -p "%m" -m "abc"` → lowercase hex)
out="$($RHASH -p '%m' -m 'abc' 2>/dev/null)"
check_eq "MD5(abc)" "900150983cd24fb0d6963f7d28e17f72" "$out"

# SHA1 of "abc"
out="$($RHASH -p '%h' -m 'abc' 2>/dev/null)"
check_eq "SHA1(abc)" "a9993e364706816aba3e25717850c26c9cd0d89d" "$out"

# SHA256 of "abc" (long-option output ends with "  (message)")
out="$($RHASH --sha256 --message 'abc' 2>/dev/null | tail -n1)"
check_prefix "SHA256(abc)" "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" "$out"

# empty message MD5 (upstream: `rhash -p "%m" -m ""` → lowercase hex)
out="$($RHASH -p '%m' -m '' 2>/dev/null)"
check_eq "MD5(empty)" "d41d8cd98f00b204e9800998ecf8427e" "$out"

# --list-hashes must be non-empty and contain MD5/SHA-256
out="$($RHASH --list-hashes 2>/dev/null | tr A-Z a-z)"
case "$out" in
    *md5*sha-256*)
        echo "ok   : --list-hashes lists MD5 and SHA-256"
        ;;
    *)
        echo "FAIL : --list-hashes missing MD5/SHA-256"
        fail=$((fail + 1))
        ;;
esac

if [ "$fail" -ne 0 ]; then
    echo "rhash CLI test: $fail assertion(s) failed"
    exit 1
fi
echo "rhash CLI test: all assertions passed"
exit 0
