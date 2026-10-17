#!/bin/sh
# aireview P3: set -euo pipefail 非 POSIX（toybox/ash 无 -o pipefail）→ 改 POSIX 兼容
set -eu
echo "=== inotify-tools smoke test ==="
inotifywait --help > /dev/null 2>&1 || { echo "FAIL: inotifywait not working"; exit 1; }
echo "inotifywait: OK"
inotifywatch --help > /dev/null 2>&1 || { echo "FAIL: inotifywatch not working"; exit 1; }
echo "inotifywatch: OK"
echo "All tests passed!"
