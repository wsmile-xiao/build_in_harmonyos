#!/bin/sh
# test_zlevis.sh — 验证 zlevis 三个脚本安装正确且 --summary 输出符合预期
# 与上游 meson test 的三个用例（zlevis/zlevis-encrypt/zlevis-decrypt --summary）对应
# 注：刻意使用 set -e 而非 set -euo pipefail——脚本为 POSIX sh（dash/busybox）
# 不保证支持 set -o pipefail，保持最大可移植性。
set -e

BINDIR="${1:-./bin}"
fail=0

check_summary() {
    script="$1"
    expected="$2"
    actual="$("$BINDIR/$script" --summary 2>/dev/null)" || { echo "FAIL: $script --summary 执行失败"; fail=1; return; }
    if [ "$actual" = "$expected" ]; then
        echo "OK: $script --summary -> $actual"
    else
        echo "FAIL: $script 输出不匹配: 期望[$expected] 实际[$actual]"
        fail=1
    fi
}

# 1. zlevis 主脚本
check_summary "zlevis" "A tool that enables automatic decryption of ZFS rpools with TPM2"
# 2. zlevis-encrypt
check_summary "zlevis-encrypt" "Encrypts using a TPM2.0 chip binding policy"
# 3. zlevis-decrypt
check_summary "zlevis-decrypt" "Decrypts a JWE using a TPM2.0 chip"

if [ "$fail" -ne 0 ]; then
    echo "TEST FAILED"
    exit 1
fi
echo "ALL ZLEVIS TESTS PASSED"
exit 0