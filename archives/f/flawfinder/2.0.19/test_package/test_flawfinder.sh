#!/bin/sh
# test_flawfinder.sh — flawfinder test_package 测试脚本
# 验证 flawfinder 可执行 + 实际扫描含漏洞样本（R34：实质调用被测包）
#
# 用法: sh test_flawfinder.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
FLAWFINDER="$BIN_DIR/flawfinder"

echo "== 1. 可执行性检查 =="
if ! "$FLAWFINDER" --version >/dev/null 2>&1 && ! "$FLAWFINDER" -V >/dev/null 2>&1; then
    echo "FAIL: flawfinder not executable" >&2
    exit 1
fi

echo "== 2. 实际源码扫描 =="
TMP_DIR=$(mktemp -d)
SAMPLE="$TMP_DIR/sample.c"
printf 'int main() {\n    char buf[10];\n    strcpy(buf, "hello world this is too long");\n    return 0;\n}\n' > "$SAMPLE"
# flawfinder 检出缺陷时返回退出码 1（正常行为），set -e 下命令替换会
# 提前终止成功路径 → 用 set +e 包住扫描，仅以输出内容判断结果
set +e
OUT=$("$FLAWFINDER" "$SAMPLE" 2>/dev/null)
RC=$?
set -e
if [ "$RC" -ne 0 ] && [ "$RC" -ne 1 ]; then
    echo "FAIL: flawfinder abnormal exit ($RC): $OUT" >&2
    exit 1
fi
if echo "$OUT" | grep -qiE "strcpy|buffer"; then
    echo "OK: flawfinder found potential flaw (strcpy/buffer)"
else
    echo "FAIL: no flaw detected in sample: $OUT" >&2
    exit 1
fi
rm -rf "$TMP_DIR"
