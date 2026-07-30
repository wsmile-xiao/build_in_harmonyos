#!/usr/bin/env bash
# Run deterministic checks against the packaged paxrelabel executable.

set -euo pipefail

PAXRELABEL_BIN="${1:?path to paxrelabel executable is required}"

case1_dir="$PWD/missing-rules"
if PAXRELABEL_SEARCH_PATH="$case1_dir" "$PAXRELABEL_BIN" 2>case1.err; then
  grep -q "relabeled 0 files" case1.err
  echo "PASS: missing rule directory is non-fatal"
else
  cat case1.err
  exit 1
fi

case2_dir="$PWD/comment-rules"
mkdir -p "$case2_dir"
printf '# comment-only rule file\n\n' > "$case2_dir/comments"
if PAXRELABEL_SEARCH_PATH="$case2_dir" "$PAXRELABEL_BIN" 2>case2.err; then
  grep -q "relabeled 0 files" case2.err
  echo "PASS: comment-only rule file leaves zero files relabeled"
else
  cat case2.err
  exit 1
fi

case3_dir="$PWD/valid-rules"
mkdir -p "$case3_dir"
printf 'pemrs %s\n' "$PWD/nonexistent-target" > "$case3_dir/valid"
if PAXRELABEL_SEARCH_PATH="$case3_dir" "$PAXRELABEL_BIN" 2>case3.err; then
  grep -q "relabeled 1 file" case3.err
  echo "PASS: valid rule is parsed and missing target is ignored as designed"
else
  cat case3.err
  exit 1
fi

case4_dir="$PWD/invalid-rules"
mkdir -p "$case4_dir"
printf 'x %s\n' "$PWD/nonexistent-target" > "$case4_dir/invalid"
if PAXRELABEL_SEARCH_PATH="$case4_dir" "$PAXRELABEL_BIN" 2>case4.err; then
  echo "FAIL: invalid flag unexpectedly succeeded"
  cat case4.err
  exit 1
fi
grep -q "invalid flag x" case4.err
echo "PASS: invalid flag fails with a diagnostic"

echo "All paxrelabel test_package checks passed"

