#!/bin/sh
# test_package/test.sh — run the memtester binary on a small region.
# Invoked by conanfile.py test() through CONFIG_SHELL bash (R5: OHOS has no
# /bin/sh, so the shebang above is informational only — bash sources this file).
#
# Usage: test.sh <path-to-memtester-binary>
set -eu

bin="$1"

# 1 MB, 1 loop: exercises every memtester test once on a 1 MiB buffer and
# exits 0 on a healthy system. memtester auto-downgrades to unlocked testing
# when mlock() returns EPERM (no CAP_IPC_LOCK), which is the common case on
# OHOS, so this still completes cleanly without privileges.
"$bin" 1M 1
