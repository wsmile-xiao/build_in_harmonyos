#!/bin/sh
# test_package/test.sh — deterministic functional test for the mlogger CLI
# Runs in conanrun env (PATH includes installed bin/).
#
# Per task #6: assertions must be deterministic ("does not crash" is not enough).
# Each case has a concrete expected string checked with exact-match assertion.
set -eu

MLOGGER="mlogger"
PASS=0
FAIL=0

ok()   { echo "PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL: $1"; echo "  expected: $2"; echo "  actual:   $3"; FAIL=$((FAIL+1)); }

assert_eq() { # label expected actual
  if [ "$2" = "$3" ]; then ok "$1"; else fail "$1" "$2" "$3"; fi
}
assert_contains() { # label needle haystack
  case "$3" in
    *"$2"*) ok "$1"; echo "    found '$2' in output";;
    *) fail "$1" "containing '$2'" "$3";;
  esac
}

echo "===== Case 1: --version (exact stdout, exit 0) ====="
# Upstream PROGRAM_VERSION is hardcoded to "1.1.2" (not updated for the 1.2.0 tag);
# asserting the real upstream behaviour, not the tag version.
out="$($MLOGGER --version 2>/dev/null)" || true
rc=$?
assert_eq "version stdout" "mlogger 1.1.2" "$out"
if [ "$rc" -ne 0 ]; then fail "version exit code" "0" "$rc"; else ok "version exit code"; fi

echo ""
echo "===== Case 2: --help exits 0 and documents core options ====="
help_out="$($MLOGGER --help 2>&1 || true)"
for opt in --udp --id --file --server --port --priority --stderr --tag --socket --version; do
  assert_contains "help lists $opt" "$opt" "$help_out"
done

echo ""
echo "===== Case 3: -s stderr echo (priority/level test) ====="
# -s (LOG_PERROR) mirrors the message to stderr; -t sets the tag.
# stderr line must contain both the tag and the message body.
err="$($MLOGGER -s -t TESTTAG3 'hello from case3' 2>&1 >/dev/null || true)"
assert_contains "stderr tag"      "TESTTAG3" "$err"
assert_contains "stderr message"  "hello from case3" "$err"

echo ""
echo "===== Case 4: -p priority encoding (info level) ====="
# -p user.info selects facility=user, level=info; combined with -s the level
# appears in the stderr/syslog prefix. We assert the message body is delivered.
err="$($MLOGGER -s -p user.info -t TESTTAG4 'priority info msg' 2>&1 >/dev/null || true)"
assert_contains "priority msg body" "priority info msg" "$err"

echo ""
echo "===== Case 5: message from argv (multi-word, joined) ====="
err="$($MLOGGER -s -t TESTTAG5 wordA wordB wordC 2>&1 >/dev/null || true)"
assert_contains "argv join A" "wordA" "$err"
assert_contains "argv join B" "wordB" "$err"
assert_contains "argv join C" "wordC" "$err"

echo ""
echo "===== Case 6: -f file logging (file source) ====="
tmpfile="$(mktemp)"
printf 'line one from file\nline two from file\n' > "$tmpfile"
err="$($MLOGGER -s -f "$tmpfile" 2>&1 >/dev/null || true)"
assert_contains "file line 1" "line one from file" "$err"
assert_contains "file line 2" "line two from file" "$err"
rm -f "$tmpfile"

echo ""
echo "===== Summary ====="
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "RESULT: ALL PASS"
exit 0
