#!/bin/sh
# test_socat.sh — consumer verification for socat 1.8.1.3 (L0c independent test source)
#
# Uses ONLY the installed `socat` binary (public CLI from the packaged bin/ dir,
# resolved via the conanrun environment exported by test_package/conanfile.py).
# Verifies observable business-layer behavior, not a print-only stub:
#   1. FILE -> FILE unidirectional relay: payload must arrive byte-identical
#   2. socat -V: must print version and exit 0
#
# /tmp may be read-only on OHOS sandboxes; use $TMPDIR (default $HOME/tmp).
set -u

fail() {
    echo "test_socat: FAIL: $*" >&2
    exit 1
}

workdir="${TMPDIR:-$HOME/tmp}/socat-test-$$"
mkdir -p "$workdir" || fail "cannot create workdir $workdir"
trap 'rm -rf "$workdir"' EXIT

infile="$workdir/in.txt"
outfile="$workdir/out.txt"
payload="consumer-verification-payload-$$"

# sanity: socat binary must be resolvable in this environment
command -v socat >/dev/null 2>&1 || fail "socat not found on PATH"
echo "$payload" > "$infile" || fail "cannot write $infile"

# 1. business-layer relay: socat -u FILE:in FILE:out,create
socat -u "FILE:$infile" "FILE:$outfile,create" || fail "socat FILE relay rc=$?"
[ -f "$outfile" ] || fail "outfile missing after relay"
got="$(cat "$outfile")" || fail "cannot read $outfile"
[ "$got" = "$payload" ] || fail "payload mismatch: got '$got' expected '$payload'"
echo "test_socat: socat relayed $(printf '%s' "$payload" | wc -c) bytes FILE->FILE OK"

# 2. CLI sanity: socat -V prints version, exit 0
socat -V > "$workdir/version.txt" 2>&1 || fail "socat -V rc=$?"
grep -qi "socat by Gerhard Rieger" "$workdir/version.txt" || fail "socat -V output missing version banner"
echo "test_socat: socat -V OK"

echo "test_socat: ALL PASS"
exit 0
