#!/usr/bin/env sh
set -eu

tmpdir="${TMPDIR:-.}/shtool-test-$$"
rm -rf "$tmpdir"
mkdir -p "$tmpdir"
trap 'rm -rf "$tmpdir"' EXIT

echo "[test] shtool version"
shtool version -ltxt -s 2.0.8 "$tmpdir/version.txt"
shtool version -ltxt -dshort "$tmpdir/version.txt" >"$tmpdir/shtool-version.out"
test "$(cat "$tmpdir/shtool-version.out")" = "2.0.8"

echo "[test] shtool echo"
out=$(shtool echo "OpenHarmony shtool")
test "$out" = "OpenHarmony shtool"

echo "[test] shtool mkdir + install"
shtool mkdir -f -p "$tmpdir/src" "$tmpdir/dst"
printf '%s\n' 'payload' > "$tmpdir/src/input.txt"
shtool install -c -m 644 "$tmpdir/src/input.txt" "$tmpdir/dst/output.txt"
test -f "$tmpdir/dst/output.txt"
test "$(cat "$tmpdir/dst/output.txt")" = "payload"

echo "[test] shtool path"
shtool path sh >"$tmpdir/shtool-path.out"
test -s "$tmpdir/shtool-path.out"

echo "[test] shtool smoke test: PASS"
