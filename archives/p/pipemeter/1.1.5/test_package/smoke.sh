#!/bin/sh
# pipemeter L1 冒烟测试（test_package）
# 真实调用包内 pipemeter 二进制并断言其行为，任何一项不符即以非零码退出。
# 用法: sh smoke.sh /absolute/path/to/pipemeter [pump-binary] [bytes]
#   pump-binary 可选：pump.c 编出来的测试数据生产者，传入后追加 T8 端到端断言
set -euo pipefail

PM="${1:-}"
PUMP="${2:-}"
PUMP_BYTES="${3:-524288}"
[ -n "$PM" ] || { echo "usage: smoke.sh <pipemeter-binary> [pump-binary] [bytes]" >&2; exit 9; }
[ -x "$PM" ] || { echo "FAIL: binary not executable: $PM" >&2; exit 9; }
if [ -n "$PUMP" ] && [ ! -x "$PUMP" ]; then
    echo "FAIL: pump not executable: $PUMP" >&2; exit 9
fi
TOTAL=7

# 临时工作目录优先落在 TMPDIR（OHOS 上 /tmp 只读，故默认 $HOME/tmp），
# 不可写时才退回当前目录——避免把中间产物写进仓库工作树。
WORKROOT="${TMPDIR:-${HOME:-.}/tmp}"
[ -d "$WORKROOT" ] && [ -w "$WORKROOT" ] || WORKROOT=.
WORK="$WORKROOT/pipemeter-smoke-$$"
rm -rf "$WORK"; mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT INT TERM

fail() { echo "FAIL: $1" >&2; exit 1; }

# --- T1 版本自检：证明安装的二进制就是 1.1.5 -----------------------------
"$PM" -V > "$WORK/v.out" 2>&1 || fail "T1 -V exit"
grep -q "pipemeter v1.1.5" "$WORK/v.out" || fail "T1 version string"

# --- T2 管道字节计量：喂 512 KiB，末行统计必须精确等于 512.00k -----------
dd if=/dev/zero bs=1024 count=512 2>/dev/null | "$PM" > "$WORK/t2.out" 2> "$WORK/t2.err"
tr '\r' '\n' < "$WORK/t2.err" | grep -q "512\.00k" || fail "T2 byte accounting"

# --- T3 数据面透传：pipemeter 不得吞掉或篡改管道内容 --------------------
dd if=/dev/zero bs=1024 count=64 2>/dev/null | "$PM" > "$WORK/t3.out" 2>/dev/null
[ "$(wc -c < "$WORK/t3.out")" -eq 65536 ] || fail "T3 payload passthrough"

# --- T4 -f 直读文件 + 多文件累加：1M + 512k 必须报 1.50M -----------------
dd if=/dev/zero bs=1024 count=1024 2>/dev/null > "$WORK/a.bin"
dd if=/dev/zero bs=1024 count=512  2>/dev/null > "$WORK/b.bin"
"$PM" -f "$WORK/a.bin" -f "$WORK/b.bin" > "$WORK/t4.out" 2> "$WORK/t4.err"
tr '\r' '\n' < "$WORK/t4.err" | grep -q "1\.50M" || fail "T4 multi-file total"

# --- T5 块大小生效：-b 64k 应回显 64.00k --------------------------------
dd if=/dev/zero bs=1024 count=256 2>/dev/null | "$PM" -b 64k > /dev/null 2> "$WORK/t5.err"
tr '\r' '\n' < "$WORK/t5.err" | grep -q "64\.00k" || fail "T5 block size"

# --- T6 非法 interval 必须以退出码 1 拒绝 --------------------------------
set +e
"$PM" -i 0 < /dev/null > /dev/null 2>&1
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "T6 bad interval exit code (got $rc)"

# --- T7 不存在的 -f 文件必须以退出码 2 报错 ------------------------------
set +e
"$PM" -f "$WORK/no-such-file" < /dev/null > /dev/null 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "T7 missing input file exit code (got $rc)"

# --- T8 端到端计量核对：pump.c 编译产物 → 包内 pipemeter ------------------
# 证明“编译出来的生产者 + 安装出来的被测二进制”在 OHOS 上真实串得通：
# pump 自报字节数 == 文件字节数 == pipemeter stdout 透传字节数 == 计量列
if [ -n "$PUMP" ]; then
    case "$PUMP_BYTES" in
        65536)   expect='64\.00k' ;;
        524288)  expect='512\.00k' ;;
        1048576) expect='1\.00M' ;;
        4194304) expect='4\.00M' ;;
        *)       expect='' ;;
    esac
    [ -n "$expect" ] || fail "T8 unsupported byte count $PUMP_BYTES"

    "$PUMP" "$PUMP_BYTES" > "$WORK/t8.in" 2> "$WORK/t8.pump"
    grep -q "wrote $PUMP_BYTES bytes" "$WORK/t8.pump" || fail "T8 pump self-report"
    [ "$(wc -c < "$WORK/t8.in")" -eq "$PUMP_BYTES" ] || fail "T8 pump byte count"

    "$PUMP" "$PUMP_BYTES" | "$PM" > "$WORK/t8.out" 2> "$WORK/t8.err"
    tr '\r' '\n' < "$WORK/t8.err" | grep -q "$expect" || fail "T8 end-to-end byte accounting ($expect)"
    [ "$(wc -c < "$WORK/t8.out")" -eq "$PUMP_BYTES" ] || fail "T8 passthrough byte count"
    TOTAL=8
fi

echo "pipemeter-test-ok $TOTAL/$TOTAL"
exit 0
