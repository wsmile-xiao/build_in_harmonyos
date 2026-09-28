#!/usr/bin/env bash
# Consumer test for the installed lsd2 CLI.
# Runs a real dating job on the upstream h1n1 example and verifies the result.
set -u

lsd2_bin="$(command -v lsd2)"
if [ -z "$lsd2_bin" ]; then
    echo "FAIL: lsd2 binary not found on PATH"
    exit 1
fi
echo "Using lsd2 at: $lsd2_bin"

# 1) Help/version smoke test (option parsing works)
"$lsd2_bin" -h > help.out 2>&1
if ! grep -q "v.1.9.9" help.out; then
    echo "FAIL: lsd2 -h did not print version banner"
    cat help.out
    exit 1
fi

# 2) Real dating run on upstream example (rooted tree + dates, 1700-nt seq)
"$lsd2_bin" -i data/h1n1_phyml.tree -d data/h1n1.date -o dating.out -s 1700 > run.log 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    echo "FAIL: lsd2 dating run exited $rc"
    tail -20 run.log
    exit 1
fi
if ! grep -q "rate" run.log; then
    echo "FAIL: lsd2 dating run produced no rate result"
    tail -20 run.log
    exit 1
fi
if [ ! -s dating.out ]; then
    echo "FAIL: lsd2 produced empty dating output"
    exit 1
fi
echo "PASS: lsd2 dating run OK"
grep -E "rate|tMRCA" run.log
exit 0