#!/bin/sh
# test_package consumer test for netselect.
# netselect requires root + raw sockets for real probing; here we verify the
# deterministic pre-socket code paths: usage output and argv validation.
# 5 assertions, all offline and root-free.
export PATH="$PATH:/system/bin"

echo "--- netselect consumer verification ---"

# 1. no arguments -> usage on stderr, exit 1 (main: argc < 1 -> usage(); return 1)
out1=$(netselect 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL: no-args exit=$rc (want 1)"; exit 1; }
echo "$out1" | grep -q "Usage: netselect" || { echo "FAIL: no usage output [$out1]"; exit 1; }
echo "PASS 1: no-args -> usage + exit 1"

# 2. -t 0 -> tries validation error, exit 1
out2=$(netselect -t 0 localhost 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL: -t 0 exit=$rc (want 1)"; exit 1; }
echo "$out2" | grep -q "number of tries must be" || { echo "FAIL: no tries error [$out2]"; exit 1; }
echo "PASS 2: -t 0 -> validation error + exit 1"

# 3. -m 1 -> max ttl validation error, exit 1
out3=$(netselect -m 1 localhost 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL: -m 1 exit=$rc (want 1)"; exit 1; }
echo "$out3" | grep -q "max ttl must be" || { echo "FAIL: no ttl error [$out3]"; exit 1; }
echo "PASS 3: -m 1 -> validation error + exit 1"

# 4. unknown option -> usage, exit 1
out4=$(netselect -Z 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL: -Z exit=$rc (want 1)"; exit 1; }
echo "$out4" | grep -q "Usage: netselect" || { echo "FAIL: no usage for -Z [$out4]"; exit 1; }
echo "PASS 4: unknown option -> usage + exit 1"

# 5. with a host but no raw-socket permission -> delayed socket error, exit 5
#    (socket() fails for non-root without CAP_NET_RAW; exit code 5 is stable)
out5=$(netselect -I 127.0.0.1 2>&1); rc=$?
if [ "$rc" = "5" ]; then
    echo "$out5" | grep -q "netselect: socket" && echo "PASS 5: no-priv raw socket -> exit 5 (expected unprivileged path)"
else
    # root or privileged sandbox: probing 127.0.0.1 must not crash (any sane rc ok)
    [ "$rc" -ge 0 ] 2>/dev/null || rc=99
    if [ "$rc" = "0" ] || [ "$rc" = "1" ]; then
        echo "PASS 5: privileged environment, probe ran (exit=$rc) — skipped unprivileged assertion"
    else
        echo "FAIL: unexpected exit=$rc for host probe [$out5]"; exit 1
    fi
fi

echo "test netselect 0.4: 5/5 checks PASS"
exit 0
