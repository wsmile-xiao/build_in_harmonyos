#!/bin/bash
# test_package/test.sh -- s-nail 14.9.25 package verification (OHOS).
# Drives the packaged s-nail binary in batch mode (no tty, no network, no MTA)
# and counts assertions explicitly.  鸿蒙特有测试：断言 1-4 全部在本包内执行。
set -u

PASS=0 FAIL=0
BIN="s-nail"

note_fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
note_pass() { echo "OK: $*"; PASS=$((PASS + 1)); }

# 定位包内 bin/s-nail（经 conanrun PATH 注入）
BIN_PATH=""
IFS=':' read -r -a _dirs <<< "${PATH}"
for d in "${_dirs[@]}"; do
    [ -n "$d" ] || continue
    if [ -x "$d/s-nail" ]; then BIN_PATH="$d/s-nail"; break; fi
done
if [ -z "$BIN_PATH" ]; then
    echo "FAIL: packaged s-nail not found on conanrun PATH"
    exit 1
fi
echo "[test] binary: $BIN_PATH"

# 1) 版本横幅：s-nail v14.9.25（自报版本一致性）
out=$("$BIN_PATH" -V 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "s-nail v14.9.25"; then
    note_pass "version banner: $out"
else
    note_fail "version banner (rc=$rc): $out"
fi

# 2) 内置命令解释器（批处理模式，-X 启动命令 + x 退出）
out=$("$BIN_PATH" -#:x -X 'echo hello-builtin' -X 'x' 2>&1)
if echo "$out" | grep -q "hello-builtin"; then
    note_pass "batch command interpreter (echo builtin via -X)"
else
    note_fail "batch command interpreter: $out"
fi

# 3) addrcodec 编码（RFC 5322 地址解析，纯内置）
out=$("$BIN_PATH" -#:x -Smta=test -X 'addrcodec enc Hey, ho <silver@go>' -X x 2>&1)
if echo "$out" | grep -q '"Hey, ho" <silver@go>'; then
    note_pass "addrcodec address encode"
else
    note_fail "addrcodec address encode: $out"
fi

# 4) -e 空邮箱检查语义：空 mailbox 返回 1（POSIX mailx -e）
: > .emptybox
"$BIN_PATH" -#:x -e -f ./.emptybox >/dev/null 2>&1
rc=$?
if [ $rc -eq 1 ]; then
    note_pass "empty-mailbox check (-e) exits 1"
else
    note_fail "empty-mailbox check (-e): rc=$rc (expected 1)"
fi

echo "s-nail test_package summary: PASS=$PASS FAIL=$FAIL TOTAL=$((PASS + FAIL))"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
