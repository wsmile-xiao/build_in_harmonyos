#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke tests for rset/3.3
# Runs in conanrun env (PATH includes the packaged bin/)
set -eu
fail() { echo "❌ $1"; exit 1; }
ok() { echo "✅ $1"; }

TMPROOT="${TMPDIR:-$(pwd)}"
T="$(mktemp -d "$TMPROOT/rset-test-XXXXXX")"
trap 'rm -rf "$T"' EXIT

# 1. rset -V reports the release version
out="$(rset -V 2>&1 || true)"
case "$out" in
  *"release: 3.3"*) ok "rset -V reports release 3.3" ;;
  *) fail "rset -V output missing 'release: 3.3': got '$out'" ;;
esac

# 2. renv quotes matching NAME="value" lines from stdin
out="$(printf 'X="1"\n' | renv -)"
[ "$out" = 'X="1"' ] || fail "renv filtering broken: got '$out'"
ok "renv filters and quotes environment lines"

# 3. renv fails on malformed lines; - -q suppresses stdout, keeps stderr error
set +e
out="$(printf 'X="1"\nDS=\n' | renv - -q 2>"$T/err")"
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "renv -q should fail on malformed input (rc=$rc)"
[ -z "$out" ] || fail "renv -q should print nothing: got '$out'"
grep -q "renv: unknown pattern: DS=" "$T/err" || fail "renv -q error message missing: '$(cat "$T/err")'"
ok "renv -q prints errors only (toybox awk argument fix verified)"

# 4. labelgrep finds a label in a pln(5) file
printf 'build:\n\trun build stage\n' > "$T/routes.pln"
out="$(labelgrep build "$T/routes.pln")"
case "$out" in
  *build*) ok "labelgrep matched 'build' label" ;;
  *) fail "labelgrep did not match label: got '$out'" ;;
esac

# 5. rinstall copies a staged file into place (uses SD staging dir)
printf 'data' > "$T/src.txt"
out="$(SD="$T" rinstall "$T/src.txt" "$T/dst.txt")"
case "$out" in
  *"rinstall: created"*) ok "rinstall created target" ;;
  *) fail "rinstall failed: got '$out'" ;;
esac
grep -q "data" "$T/dst.txt" || fail "rinstall target content mismatch"
ok "rinstall content verified"

# 6. miniquark binary is runnable (prints usage on no args)
out="$(miniquark 2>&1 || true)"
case "$out" in
  *usage:\ miniquark*) ok "miniquark runs" ;;
  *) fail "miniquark unexpected output: '$out'" ;;
esac

echo "All rset test_package checks passed."
