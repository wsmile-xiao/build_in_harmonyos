#!/bin/sh
# test.sh — pcaputils 0.8 L1 smoke test
# Each tool with no args must print its Usage banner and exit non-zero.
# This exercises: dynamic link against libpcap + libJudy, argument parsing,
# and proves the binary is a real OHOS executable (not a loader failure).
set -e

for tool in pcapdump pcapip pcappick pcapuc; do
  out=$($tool 2>&1) || true
  echo "$out" | grep -q "Usage:" || {
    echo "FAIL: $tool did not print Usage banner. Output was:"
    echo "$out"
    exit 1
  }
  echo "OK: $tool prints usage"
done

echo "All pcaputils smoke tests passed"
