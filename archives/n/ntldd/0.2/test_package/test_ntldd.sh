#!/data/service/hnp/bin/bash
# test_package/test_ntldd.sh — consumer checks for the installed ntldd binary.
# Runs in conanrun env; the binary path is passed as $1.
set -eu

NTLDD="${1:?usage: test_ntldd.sh <path-to-ntldd>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PASS=0

echo "[test] 1/6 --version reports 0.2"
"$NTLDD" --version | grep -q "ntldd 0.2"
echo "  ok"
PASS=$((PASS + 1))

echo "[test] 2/6 --help prints usage"
"$NTLDD" --help | grep -q "Usage:"
echo "  ok"
PASS=$((PASS + 1))

if command -v python3 >/dev/null 2>&1; then
  # OHOS: /tmp is read-only (E002); keep temp files under TMPDIR or $HOME.
  TMPDIR_T="$(mktemp -d "${TMPDIR:-$HOME}/ntldd-test.XXXXXX")"
  trap 'rm -rf "$TMPDIR_T"' EXIT
  python3 "$HERE/gen_pe.py" "$TMPDIR_T/tiny.exe" >/dev/null

  echo "[test] 3/6 lists KERNEL32.dll dependency"
  OUT="$("$NTLDD" "$TMPDIR_T/tiny.exe")"
  echo "$OUT" | grep -q "KERNEL32.dll"
  echo "  ok"
  PASS=$((PASS + 1))

  echo "[test] 4/6 lists advapi32.dll dependency"
  echo "$OUT" | grep -q "advapi32.dll"
  echo "  ok"
  PASS=$((PASS + 1))

  echo "[test] 5/6 unresolved DLLs are reported, not silently dropped"
  echo "$OUT" | grep -q "not found"
  echo "  ok"
  PASS=$((PASS + 1))

  echo "[test] 6/6 -i lists imported symbol Foo"
  "$NTLDD" -i "$TMPDIR_T/tiny.exe" | grep -q "Foo"
  echo "  ok"
  PASS=$((PASS + 1))
else
  echo "[test] python3 unavailable: tests 3-6 skipped (degraded)"
fi

echo "test_ntldd: $PASS assertions passed"
test "$PASS" -ge 2
