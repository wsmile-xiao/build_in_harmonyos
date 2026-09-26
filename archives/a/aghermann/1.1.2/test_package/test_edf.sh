#!/bin/bash
# R34/L0c 实质测试：用被测包 bin/edfhed 解析一个按 EDF 规范构造的
# 最小 2 通道 EDF 文件，断言输出含 "# of channels : 2"。
# 用法: test_edf.sh <pkg_bin_dir> <minimal.edf>
#   <pkg_bin_dir>  — 被测包 package_folder/bin（含 edfhed）
#   <minimal.edf>  — 测试用 EDF 文件（由 conanfile.py test() 生成）
set -euo pipefail

BIN_DIR="${1:-}"
EDF_FILE="${2:-}"
if [ -z "$BIN_DIR" ] || [ -z "$EDF_FILE" ]; then
    echo "ERROR: usage: test_edf.sh <pkg_bin_dir> <minimal.edf>"
    exit 2
fi

EDFHED="$BIN_DIR/edfhed"
if [ ! -x "$EDFHED" ]; then
    echo "ERROR: edfhed not found/executable at $EDFHED"
    exit 1
fi
if [ ! -f "$EDF_FILE" ]; then
    echo "ERROR: EDF file not found: $EDF_FILE"
    exit 1
fi

# 实际运行 edfhed 解析 EDF（依赖共享库由 conanrun env 注入 LD_LIBRARY_PATH）
OUT="$("$EDFHED" "$EDF_FILE" 2>&1)" || {
    echo "ERROR: edfhed exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

# 断言解析出 2 通道（EDF 头构造正确 → 解析器读到 n_channels=2）
if ! echo "$OUT" | grep -q "# of channels[[:space:]]*:[[:space:]]*2"; then
    echo "ERROR: expected '# of channels : 2' in edfhed output"
    exit 1
fi

echo "[ok] edfhed parsed 2-channel EDF (R34 substantive test passed)"
