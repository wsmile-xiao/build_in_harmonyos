#!/bin/sh
set -eu

binary=$1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

dd if=/dev/zero of="$work/gzip.img" bs=1024 count=1 2>/dev/null
printf '\037\213' | dd of="$work/gzip.img" bs=1 seek=0 conv=notrunc 2>/dev/null
dd if=/dev/zero of="$work/unknown.img" bs=1024 count=128 2>/dev/null

tests=0
check() {
    description=$1
    expected_rc=$2
    expected=$3
    shift 3
    set +e
    actual=$("$@" 2>"$work/stderr")
    rc=$?
    set -e
    tests=$((tests + 1))
    if [ "$rc" -ne "$expected_rc" ] || [ "$actual" != "$expected" ]; then
        echo "FAIL $description: rc=$rc output=$actual" >&2
        cat "$work/stderr" >&2
        exit 1
    fi
    echo "PASS $description"
}

check "gzip image from file" 0 "FSTYPE=gzip
FSSIZE=0" "$binary" "$work/gzip.img"
check "gzip image from stdin" 0 "FSTYPE=gzip
FSSIZE=0" "$binary" - < "$work/gzip.img"
check "unknown image" 1 "FSTYPE=unknown
FSSIZE=0" "$binary" "$work/unknown.img"
check "invalid argument count" 1 "" "$binary" one two
printf 'consumer assertions: %s/%s passed\n' "$tests" "$tests"
