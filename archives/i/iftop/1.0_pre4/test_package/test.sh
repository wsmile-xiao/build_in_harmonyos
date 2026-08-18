#!/bin/sh
# test_package consumer test — iftop 1.0_pre4 (CLI tool).
#
# Runs the INSTALLED iftop binary (on PATH via VirtualRunEnv) in the only
# safe, unprivileged consumer scenario it supports without root / network
# capture / live traffic: `iftop -h` help output.
#
# Assertions check real output AND exit code; this is not an existence
# check and not a stub. It never opens an interface or captures packets.
#
# Note: iftop has no `--version` option; `iftop --version` prints the
# version line but exits 1 (unknown option), so it is not a pass scenario.
#
# Requires: PATH contains the package bin/ dir (VirtualRunEnv conanrun).

set -u

fail=0

# case 1: iftop -h exits 0
out="$(iftop -h 2>&1)"
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "[PASS] case1: iftop -h 退出码=0"
else
    echo "[FAIL] case1: iftop -h 退出码=$rc，期望 0"
    fail=1
fi

# case 2: synopsis line present
if echo "$out" | grep -q "display bandwidth usage on an interface by host"; then
    echo "[PASS] case2: synopsis 行存在"
else
    echo "[FAIL] case2: 未找到 synopsis 'display bandwidth usage on an interface by host'"
    fail=1
fi

# case 3: version line present
if echo "$out" | grep -q "iftop, version 1.0pre4"; then
    echo "[PASS] case3: 版本行 'iftop, version 1.0pre4' 存在"
else
    echo "[FAIL] case3: 未找到版本行 'iftop, version 1.0pre4'"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "[PASS] iftop consumer test: 3/3 cases passed"
    exit 0
fi
exit 1
