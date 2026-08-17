#!/system/bin/sh
set -eu

echo "[test 1] help contains --remote"
HELP_OUTPUT="$(adbtuifm --help 2>&1)"
printf "%s\n" "$HELP_OUTPUT" | grep -q -- "--remote" || {
    echo "FAIL: --remote not found"
    exit 1
}

echo "[test 2] help contains --local"
printf "%s\n" "$HELP_OUTPUT" | grep -q -- "--local" || {
    echo "FAIL: --local not found"
    exit 1
}

echo "[test 3] invalid local path is rejected"
INVALID_OUTPUT="$(adbtuifm --local /this/path/does/not/exist 2>&1 || true)"
printf "%s\n" "$INVALID_OUTPUT" | grep -q "Invalid local path" || {
    echo "FAIL: invalid local path was not rejected"
    echo "$INVALID_OUTPUT"
    exit 1
}

echo "All 3 tests passed."
