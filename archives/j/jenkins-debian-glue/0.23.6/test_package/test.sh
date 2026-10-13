#!/bin/bash
# Replay of the upstream `make check` suite (shunit2-based, not available on
# OHOS) against the packaged jenkins-debian-glue scripts.
#
# Usage: test.sh <jdg-bindir> <fixtures-dir>
# Exit 0 + prints PASSED on success; prints FAILED and exits 1 otherwise.
#
# Sources:
#   tests/increase-version-number  (13 assertions, replayed 1:1)
#   tests/merge-conflict           (3 assertions, replayed 1:1)
#   tests/file-detection           (2 assertions; the bracketed mimetype
#                                   text comes from the platform file(1)
#                                   implementation, so only the stable
#                                   prefix/suffix is asserted)
#   + 3 supplement assertions for the tap/jdg-tap-pep8 mimetype gate
#     (upstream has no pep8 test; uses a fake pycodestyle shim, mirroring
#     the upstream tests/file-detection fake-shim convention)

set -euo pipefail
BIN="$1"
FIX="$2"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2" got="$3"
  if [ "$expected" = "$got" ]; then
    PASS=$((PASS + 1))
    echo "ok - $desc"
  else
    FAIL=$((FAIL + 1))
    echo "not ok - $desc"
    echo "  expected: [$expected]"
    echo "  got:      [$got]"
  fi
}

check_contains() {
  local desc="$1" needle="$2" got="$3"
  case "$got" in
    *"$needle"*)
      PASS=$((PASS + 1))
      echo "ok - $desc"
      ;;
    *)
      FAIL=$((FAIL + 1))
      echo "not ok - $desc"
      echo "  needle: [$needle]"
      echo "  got:    [$got]"
      ;;
  esac
}

INCVER="$BIN/jdg-increase-version-number"
MERGE="$BIN/jdg-tap-merge-conflict"
SHELLCHECK_TAP="$BIN/jdg-tap-shellcheck"
PERLCRITIC_TAP="$BIN/jdg-tap-perlcritic"
PEP8_TAP="$BIN/jdg-tap-pep8"

PY_FILE="$FIX/pep8/sample.py"
SHELL_FIX="$FIX/file-detection/test.sh"

KO_FILE="$FIX/merge-conflict/ko.txt"
OK_FILE="$FIX/merge-conflict/ok.txt"
KO_OUT="1..3
not ok 1           1:<<<<<<< HEAD
not ok 2           3:=======
not ok 3           5:>>>>>>> 47509bb6 (MT#58115 WIP)"

# ── tests/increase-version-number ─────────────────────────────
check "increase-version-number 0.23"   "0.23+0"       "$("$INCVER" 0.23)"
check "increase-version-number 23"     "23+0"         "$("$INCVER" 23)"
check "increase-version-number 0.23-1" "0.23-1+0"     "$("$INCVER" 0.23-1)"
check "increase-version-number 0.1.23-1" "0.1.23-1+0" "$("$INCVER" 0.1.23-1)"
check "increase-version-number 0.1.23-3" "0.1.23-3+0" "$("$INCVER" 0.1.23-3)"
check "increase-version-number 1:0.42-2" "1:0.42-2+0" "$("$INCVER" 1:0.42-2)"
check "increase-version-number 2008.01.02" "2008.01.02+0" "$("$INCVER" 2008.01.02)"
check "increase-version-number 0.42~2" "0.42~2+0"     "$("$INCVER" 0.42~2)"
check "increase-version-number 0.9.0"  "0.9.0+0"      "$("$INCVER" 0.9.0)"
check "increase-version-number 0.9.00" "0.9.00+0"     "$("$INCVER" 0.9.00)"
check "increase-version-number 0.8"    "0.8+0"        "$("$INCVER" 0.8)"
check "increase-version-number 0.9"    "0.9+0"        "$("$INCVER" 0.9)"
check "increase-version-number 3.1.4+1" "3.1.4+1+0"   "$("$INCVER" 3.1.4+1)"

# ── tests/merge-conflict ──────────────────────────────────────
check "merge-conflict KO detection" "$KO_OUT" "$("$MERGE" "$KO_FILE")"
check "merge-conflict clean file yields no output" "" "$("$MERGE" "$OK_FILE")"
check_contains "merge-conflict directory input ignored" \
               "is a directory. Ignoring." "$("$MERGE" "$FIX" 2>&1)"

# ── tests/file-detection ──────────────────────────────────────
# Upstream puts fake shellcheck/perlcritic shims first on PATH.
FILE_TEST="$FIX/file-detection/test.sh"
check "file-detection: shellcheck TAP on fixture" "1..0" \
      "$(PATH="$FIX/file-detection:$PATH" "$SHELLCHECK_TAP" "$FILE_TEST")"
check_contains "file-detection: non-perl file gracefully ignored" \
               "doesn't look like perl" \
               "$(PATH="$FIX/file-detection:$PATH" "$PERLCRITIC_TAP" "$FILE_TEST" 2>&1)"
check_contains "file-detection: perlcritic message ends with Ignoring." \
               "Ignoring." \
               "$(PATH="$FIX/file-detection:$PATH" "$PERLCRITIC_TAP" "$FILE_TEST" 2>&1)"

# ── tap/jdg-tap-pep8 mimetype gate ────────────────────────────
# Upstream has no dedicated pep8 test; this mirrors the upstream
# tests/file-detection approach (fake tool shims first on PATH).
# Covers the mimetype detection regression fixed in
# 0001-ohos-portability.patch: `file -b` output must still be
# matched by the (broadened) /python/i regex.
PEP8_PATH="$FIX/pep8:$PATH"
# Negative: a shell script must be ignored (exit 0, gate message).
check_contains "pep8: non-python file ignored" \
               "doesn't look like Python" \
               "$(PATH="$PEP8_PATH" "$PEP8_TAP" "$SHELL_FIX" 2>&1)"
# Positive: a Python file passes the gate and is handed to the
# (shimmed) pycodestyle tool -> no issues, empty output, exit 0.
check "pep8: python file passes gate, lints clean" "" \
      "$(PATH="$PEP8_PATH" "$PEP8_TAP" "$PY_FILE" 2>&1)"

echo "summary: pass=$PASS fail=$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "PASSED"
exit 0
