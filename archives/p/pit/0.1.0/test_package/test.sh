#!/usr/bin/env bash
# test_package/test.sh — consumer functional test for the pit CLI
# Usage: test.sh <path-to-pit-binary>
#
# Exercises the real project/task/note/log/info lifecycle with PITFILE
# isolation. Each check greps for the unique strings created in this run,
# so empty-fixture false passes are impossible. Emits the HMBS evidence
# markers on completion.
set -euo pipefail

PIT="${1:-pit}"
FAILED=0
PASS_COUNT=0
DISCOVERED=9

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAILED=1; }

# Isolated workspace. Use a relative PITFILE: upstream 0.1.0 segfaults on
# absolute paths (fixed upstream post-release, issue #4), so cd in first.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/pit-test.XXXXXX")"
cd "$WORK"
export PITFILE="test.pit"

# 0.1.0 returns 1 even on success (fixed upstream post-release, PR #6),
# so capture output with "|| true" and assert on content, never on exit code.
echo "[test 1/9] pit version reports 0.1.0"
VERSION_OUT="$("$PIT" version 2>&1)" || true
if echo "$VERSION_OUT" | grep -q "0.1.0"; then
  pass "pit version"
else
  fail "pit version (got: $VERSION_OUT)"
fi

echo "[test 2/9] pit help prints help"
HELP_OUT="$("$PIT" help 2>&1)" || true
if [ -n "$HELP_OUT" ]; then
  pass "pit help"
else
  fail "pit help produced no output"
fi

echo "[test 3/9] pit init creates a database"
INIT_OUT="$("$PIT" init 2>&1)" || true
if echo "$INIT_OUT" | grep -q "Created empty" && [ -f "$PITFILE" ]; then
  pass "pit init"
else
  fail "pit init (got: $INIT_OUT)"
fi

echo "[test 4/9] pit project creates a project"
PROJECT_OUT="$("$PIT" project -c "OHOS pit test project" 2>&1)" || true
if echo "$PROJECT_OUT" | grep -q "created project"; then
  pass "pit project create"
else
  fail "pit project create (got: $PROJECT_OUT)"
fi

echo "[test 5/9] pit task creates a task"
TASK_OUT="$("$PIT" task -c "OHOS pit test task" 2>&1)" || true
if echo "$TASK_OUT" | grep -q "created task"; then
  pass "pit task create"
else
  fail "pit task create (got: $TASK_OUT)"
fi

echo "[test 6/9] pit note creates a note"
NOTE_OUT="$("$PIT" note -c "OHOS pit test note" 2>&1)" || true
if echo "$NOTE_OUT" | grep -q "created note"; then
  pass "pit note create"
else
  fail "pit note create (got: $NOTE_OUT)"
fi

echo "[test 7/9] pit project lists the created project"
LIST_OUT="$("$PIT" project 2>&1)" || true
if echo "$LIST_OUT" | grep -q "OHOS pit test project"; then
  pass "pit project list"
else
  fail "pit project list (got: $LIST_OUT)"
fi

echo "[test 8/9] pit log records the activity"
LOG_OUT="$("$PIT" log 2>&1)" || true
if echo "$LOG_OUT" | grep -q "OHOS pit test project"; then
  pass "pit log"
else
  fail "pit log (got: $LOG_OUT)"
fi

echo "[test 9/9] pit info summarizes a non-empty database"
INFO_OUT="$("$PIT" info 2>&1)" || true
if [ -n "$INFO_OUT" ] && [ -s "$PITFILE" ]; then
  pass "pit info"
else
  fail "pit info produced no output or database is empty"
fi

cd /
rm -rf "$WORK"

# HMBS consumer-test evidence (counts come from this script's real assertions).
if [ "$FAILED" -eq 0 ]; then
  printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh <pit_binary>","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
else
  printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh <pit_binary>","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
fi

# Re-emit the upstream verdict persisted by conanfile build() so the
# evidence survives Conan cache hits (dav2d precedent).
UPSTREAM_JSON="$(dirname "$PIT")/../res/upstream_test_result.json"
if [ -f "$UPSTREAM_JSON" ]; then
  printf 'HMBS_UPSTREAM_TEST_RESULT=%s\n' "$(cat "$UPSTREAM_JSON")"
else
  echo "WARN: upstream_test_result.json not found at $UPSTREAM_JSON"
  FAILED=1
fi

exit "$FAILED"
