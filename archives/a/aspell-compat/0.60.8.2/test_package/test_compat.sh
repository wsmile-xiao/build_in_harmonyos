#!/bin/sh
# test_compat.sh — aspell-compat 0.60.8.2 实质测试脚本（CI L0c 要求的测试源文件）
#
# 用法: test_compat.sh <bin_dir>
# 校验被测包 bin/ispell、bin/spell:
#   1. 存在且可执行
#   2. sh -n 语法校验（实际调用 shell 解析器）
#   3. 内容确实包装 aspell CLI
set -u

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "usage: test_compat.sh <bin_dir>" >&2
    exit 2
fi

fail=0
for script in ispell spell; do
    path="$BIN_DIR/$script"
    if [ ! -f "$path" ]; then
        echo "FAIL: missing compat script: $path" >&2
        fail=1
        continue
    fi
    if [ ! -x "$path" ]; then
        echo "FAIL: compat script not executable: $path" >&2
        fail=1
        continue
    fi
    if ! sh -n "$path"; then
        echo "FAIL: sh -n syntax error: $path" >&2
        fail=1
        continue
    fi
    if ! grep -q "aspell" "$path"; then
        echo "FAIL: $script does not reference aspell CLI" >&2
        fail=1
        continue
    fi
    echo "OK: $script exists, executable, valid sh, wraps aspell"
done

if [ "$fail" -ne 0 ]; then
    echo "aspell-compat test FAILED" >&2
    exit 1
fi
echo "aspell-compat test PASSED"
exit 0
