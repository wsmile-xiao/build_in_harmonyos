#!/usr/bin/zsh
# test_jhead.sh — Verify jhead binary works
# Usage: zsh test_jhead.sh /path/to/jhead
set -euo pipefail

JHEAD="$1"
if [ -z "$JHEAD" ]; then
    echo "ERROR: jhead binary path not provided"
    exit 1
fi

# Test 1: Version output
output=$("$JHEAD" -V 2>&1)
echo "$output"
case "$output" in
    *"Jhead version: 3.08"*)
        echo "        [ok] version check"
        ;;
    *)
        echo "        [fail] version mismatch"
        exit 1
        ;;
esac

# Test 2: Help output (should contain usage info)
# jhead -h may exit non-zero (usage flag), so suppress exit code
output=$("$JHEAD" -h 2>&1 || true)
echo "$output" | head -5
case "$output" in
    *"usage"*|*"Usage"*|*"Jhead"*|*"Exif"*)
        echo "        [ok] help output"
        ;;
    *)
        echo "        [fail] no help output"
        exit 1
        ;;
esac

echo "All tests passed."
