#!/bin/sh
# test_package/test_smoke.sh — x3270 消费者冒烟测试（R34 实质验证）
#
# 由 test_package/conanfile.py 的 test() 方法调用，直接执行被测包二进制。
# 满足 CI L0c（test_package 下必须存在测试源文件）：
#   任一二进制缺失或 --version 退出非 0 → 脚本整体失败。
# 包产物被移除（CI L1e 破坏性反向验证）时二进制必然缺失 → 测试必然失败，
# 从而通过"测试是否实质依赖包产物"的逆向检测（非 stub/fake test）。

set -u

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "[test_smoke] FAIL: bin dir not found: ${BIN_DIR}"
    exit 1
fi

FAILED=0
for BIN in s3270 c3270 pr3287; do
    if [ -x "${BIN_DIR}/${BIN}" ]; then
        if "${BIN_DIR}/${BIN}" --version >/dev/null 2>&1; then
            echo "[test_smoke] OK: ${BIN} --version (exit 0)"
        else
            echo "[test_smoke] FAIL: ${BIN} --version exited non-zero"
            FAILED=1
        fi
    else
        echo "[test_smoke] FAIL: ${BIN} not found or not executable in ${BIN_DIR}"
        FAILED=1
    fi
done

exit ${FAILED}
