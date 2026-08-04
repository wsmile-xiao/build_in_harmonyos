#!/usr/bin/env bash
set -euo pipefail

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local label="$3"
  if ! printf '%s' "$haystack" | grep -Fq -- "$needle"; then
    echo "FAIL: $label"
    echo "$haystack"
    exit 1
  fi
  echo "PASS: $label"
}

run_capture() {
  set +e
  CAPTURE_OUTPUT="$("$@" 2>&1)"
  CAPTURE_RC=$?
  set -e
  echo "[cmd] $*"
  echo "$CAPTURE_OUTPUT"
}

run_capture pdnsd --version
if [ "$CAPTURE_RC" -ne 1 ]; then
  echo "FAIL: pdnsd --version exited $CAPTURE_RC, expected upstream-defined 1"
  exit 1
fi
version_output="$CAPTURE_OUTPUT"
assert_contains "$version_output" "pdnsd - dns proxy daemon" "pdnsd --version reports program name"
assert_contains "$version_output" "1.2.9a" "pdnsd --version reports upstream version"

run_capture pdnsd --help
if [ "$CAPTURE_RC" -ne 1 ]; then
  echo "FAIL: pdnsd --help exited $CAPTURE_RC, expected upstream-defined 1"
  exit 1
fi
help_output="$CAPTURE_OUTPUT"
assert_contains "$help_output" "Usage: pdnsd" "pdnsd --help reports usage"
assert_contains "$help_output" "--config-file" "pdnsd --help reports config option"

run_capture pdnsd-ctl version
if [ "$CAPTURE_RC" -ne 0 ]; then
  echo "FAIL: pdnsd-ctl version exited $CAPTURE_RC"
  exit 1
fi
ctl_version="$CAPTURE_OUTPUT"
assert_contains "$ctl_version" "pdnsd-ctl" "pdnsd-ctl version reports program name"
assert_contains "$ctl_version" "1.2.9a" "pdnsd-ctl version reports upstream version"

run_capture pdnsd-ctl help
if [ "$CAPTURE_RC" -ne 0 ]; then
  echo "FAIL: pdnsd-ctl help exited $CAPTURE_RC"
  exit 1
fi
ctl_help="$CAPTURE_OUTPUT"
assert_contains "$ctl_help" "Usage: pdnsd-ctl" "pdnsd-ctl help reports usage"

run_capture pdnsd --definitely-invalid-option
invalid_output="$CAPTURE_OUTPUT"
if [ "$CAPTURE_RC" -eq 0 ]; then
  echo "FAIL: invalid pdnsd option unexpectedly succeeded"
  echo "$invalid_output"
  exit 1
fi
assert_contains "$invalid_output" "unknown option" "invalid option is rejected"

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"cases":5,"assertions":10,"command":"bash test.sh"}'
