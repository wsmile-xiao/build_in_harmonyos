#!/usr/bin/env bash
# test_hashrat.sh — test_package 物理测试源文件（L0c 门禁要求）
#
# 消费者视角验证 hashrat 1.25 CLI：通过安装产物 bin/hashrat 的公开
# 命令行接口断言版本输出、SHA-256 已知向量与退出码语义（与上游
# check.sh TestExitCodes 一致：命中=0、未命中=1）。
#
# 用法: test_hashrat.sh <hashrat 二进制绝对路径>
set -u

HASHRAT="${1:-}"
if [ -z "$HASHRAT" ] || [ ! -x "$HASHRAT" ]; then
    echo "[fail] hashrat binary missing or not executable: '$HASHRAT'" >&2
    exit 1
fi

FAILURES=0

check_eq() { # $1 name  $2 actual  $3 expected
    if [ "$2" = "$3" ]; then
        echo "[pass] $1"
    else
        echo "[fail] $1: got '$2', want '$3'" >&2
        FAILURES=$((FAILURES + 1))
    fi
}

# 1) 版本冒烟（上游 -version 输出为 "version: 1.25"；按内容断言）
VER_OUT="$("$HASHRAT" -version 2>&1)"
check_eq "-version output" "$VER_OUT" "version: 1.25"

# 2) SHA-256 已知向量（与 check.sh TestHash sha256 同一输入/期望）
VECTOR="The sky above the port was the color of television, tuned to a dead channel. "
EXPECTED_SHA256="c7fadad016311a935a56dcdfb585cf5a4781073f7da13afa22177796e566434f"
SHA_OUT="$(printf '%s' "$VECTOR" | "$HASHRAT" -sha256 2>&1)"
check_eq "sha256 known vector" "$SHA_OUT" "$EXPECTED_SHA256"

# 3) 退出码语义（与 check.sh TestExitCodes HashFile 一致：命中=0、未命中=1）
#    HMDFS 环境下 stdout 重定向到 /dev/null 时哈希会挂起（实测 rc=124），
#    因此用命令替换捕获输出（管道语义，与 -version/-sha256 探针相同）；
#    探针文件写入当前（可写共享）目录并事后清理。
PROBE_FILE=".hashrat-rc-probe-$$.txt"
printf 'exit code probe' > "$PROBE_FILE"
RC_FOUND_OUT="$("$HASHRAT" -md5 "$PROBE_FILE" 2>&1)"
RC_FOUND=$?
RC_NOTFOUND_OUT="$("$HASHRAT" -md5 "$PROBE_FILE.no-such" 2>&1)"
RC_NOTFOUND=$?
if [ -n "$PROBE_FILE" ] && [ -f "$PROBE_FILE" ]; then
    rm -f "$PROBE_FILE"
fi
check_eq "exit code (existing file)" "$RC_FOUND" "0"
check_eq "exit code (missing file)" "$RC_NOTFOUND" "1"

if [ "$FAILURES" -eq 0 ]; then
    echo "[ok] test_hashrat.sh: ALL CHECKS PASSED"
    exit 0
fi
echo "[fail] test_hashrat.sh: $FAILURES check(s) failed" >&2
exit 1
