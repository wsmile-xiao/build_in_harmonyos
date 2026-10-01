#!/bin/sh
# test_tiger.sh — functional smoke test for an installed tiger package.
#
# Usage: test_tiger.sh <package-folder>
#
# The script is intentionally POSIX (no bashisms) so that it runs under the
# HarmonyOS toybox shell, and it only uses utilities that ship with the device
# (grep, head, sed, mkdir, rm).
#
# What is verified:
#   1. installation layout (commands in bin/, tiger home in share/tiger/)
#   2. the shebang of bin/tiger resolves to an interpreter that exists (E165)
#   3. the five helper binaries built from c/ are installed and executable
#   4. md5 matches the RFC 1321 vectors          -> patch 0001 on this ABI
#   5. snefru matches the upstream test vector   -> patch 0001 on this ABI
#   6. realpath resolves an existing path
#   7. getpermit reports owner/group/permission bits
#   8. tigexp explains a message id from doc/explain.idx -> patch 0002
#   9. tiger -h / tiger -v work through the installed config

set -u

PKG=${1:-}
if [ -z "$PKG" ]; then
    echo "usage: $0 <package-folder>" >&2
    exit 1
fi

BIN="$PKG/bin"
TIGERHOME="$PKG/share/tiger"
HELPERS="$TIGERHOME/bin"

ASSERTIONS=0
pass() { ASSERTIONS=$((ASSERTIONS + 1)); echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

WORK=${TMPDIR:-${HOME:-.}}/tiger-test-$$
mkdir -p "$WORK" || fail "cannot create work directory $WORK"
trap 'rm -rf "$WORK"' EXIT INT TERM

# ── 1. installation layout ───────────────────────────────────────────────────
for f in "$BIN/tiger" "$BIN/tigexp" "$BIN/tigercron"; do
    [ -s "$f" ] || fail "missing installed command: $f"
    [ -x "$f" ] || fail "installed command is not executable: $f"
done
for f in "$TIGERHOME/config" "$TIGERHOME/initdefs" "$TIGERHOME/syslist" \
         "$TIGERHOME/doc/explain.idx" "$TIGERHOME/scripts/check_accounts" \
         "$PKG/etc/tiger/tigerrc" "$PKG/etc/tiger/cronrc"; do
    [ -s "$f" ] || fail "missing installed data file: $f"
done
[ -d "$TIGERHOME/systems/Linux" ] || fail "missing platform data: $TIGERHOME/systems/Linux"
[ -d "$TIGERHOME/systems/default" ] || fail "missing platform data: $TIGERHOME/systems/default"
pass "installation layout: bin/, share/tiger/ and etc/tiger/ are populated"

# ── 2. interpreter of the installed commands (E165) ──────────────────────────
for cmd in tiger tigexp tigercron; do
    interp=$(head -n 1 "$BIN/$cmd" | sed -e 's/^#!//' -e 's/[[:space:]].*$//')
    [ -n "$interp" ] || fail "bin/$cmd has no shebang"
    [ -x "$interp" ] || fail "bin/$cmd shebang interpreter does not exist: $interp"
done
pass "bin/{tiger,tigexp,tigercron} shebangs resolve to an existing interpreter"

# ── 3. helper binaries built from c/ ─────────────────────────────────────────
for helper in getpermit snefru md5 testsuid realpath; do
    [ -x "$HELPERS/$helper" ] || fail "missing helper binary: $HELPERS/$helper"
done
pass "c/ helper binaries installed: getpermit snefru md5 testsuid realpath"

# ── 4. md5 correctness (RFC 1321 vectors, patch 0001) ────────────────────────
out=$("$HELPERS/md5" -sabc 2>&1) || fail "md5 -sabc failed: $out"
echo "$out" | grep -q "900150983cd24fb0d6963f7d28e17f72" \
    || fail "md5(\"abc\") is wrong on this ABI: $out"
pass "md5(\"abc\") == 900150983cd24fb0d6963f7d28e17f72"

out=$(printf 'message digest' | "$HELPERS/md5" 2>&1) || fail "md5 over stdin failed: $out"
echo "$out" | grep -q "f96b697d7cb7938d525a2f31aaf161d0" \
    || fail "md5(\"message digest\") is wrong on this ABI: $out"
pass "md5(\"message digest\") == f96b697d7cb7938d525a2f31aaf161d0 (stdin)"

# ── 5. snefru correctness (vector documented in c/snefru.c, patch 0001) ──────
out=$(printf '123456789\n' | "$HELPERS/snefru" 2>&1) || fail "snefru failed: $out"
echo "$out" | grep -q "4ca72639 e40e9ab9 c0c3f523 c4449b39" \
    || fail "snefru(\"123456789\") is wrong on this ABI: $out"
pass "snefru(\"123456789\") == 4ca72639 e40e9ab9 c0c3f523 c4449b39"

# ── 6. realpath ──────────────────────────────────────────────────────────────
mkdir -p "$WORK/sub" || fail "cannot create $WORK/sub"
: > "$WORK/sub/file"
out=$(cd "$WORK" && "$HELPERS/realpath" sub/file 2>&1) || fail "realpath failed: $out"
case "$out" in
    /*) ;;
    *) fail "realpath did not return an absolute path: $out" ;;
esac
[ -f "$out" ] || fail "realpath returned a non-existent path: $out"
case "$out" in
    */sub/file) ;;
    *) fail "realpath did not resolve sub/file: $out" ;;
esac
pass "realpath resolves sub/file to an absolute existing path"

# ── 7. getpermit ─────────────────────────────────────────────────────────────
out=$("$HELPERS/getpermit" "$BIN/tiger" 2>&1) || fail "getpermit failed: $out"
set -- $out
[ "$1" = "$BIN/tiger" ] || fail "getpermit did not report the file path: $out"
[ $# -ge 13 ] || fail "getpermit output is incomplete: $out"
pass "getpermit reports owner, group and permission bits for bin/tiger"

# ── 8. tigexp explains a message id (patch 0002) ─────────────────────────────
# TIGERHOMEDIR is tiger's documented way to relocate an installation.
out=$(TIGERHOMEDIR="$TIGERHOME" "$BIN/tigexp" init001e 2>&1)
echo "$out" | grep -q "does not have a value" \
    || fail "tigexp did not explain init001e: $out"
pass "tigexp init001e returns the explanation documented in doc/config.txt"

# ── 9. tiger command line entry points ───────────────────────────────────────
out=$("$BIN/tiger" -B "$TIGERHOME" -h 2>&1) || fail "tiger -h failed: $out"
echo "$out" | grep -q "Usage:" || fail "tiger -h did not print the usage text: $out"
pass "tiger -B <tigerhome> -h prints the usage summary"

out=$("$BIN/tiger" -B "$TIGERHOME" -v 2>&1) || fail "tiger -v failed: $out"
echo "$out" | grep -q "tiger, version" || fail "tiger -v did not report a version: $out"
pass "tiger -B <tigerhome> -v reports its version"

echo ""
echo "All $ASSERTIONS assertions passed."
