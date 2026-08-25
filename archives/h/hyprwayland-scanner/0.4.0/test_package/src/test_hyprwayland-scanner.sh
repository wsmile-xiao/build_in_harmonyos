#!/bin/sh
# test_hyprwayland-scanner.sh — hyprwayland-scanner 工具消费者验证脚本
#
# 验证 hyprwayland-scanner 可执行文件可被真实消费：
#   1) 产物存在性：bin/hyprwayland-scanner 存在且可执行
#   2) 真实代码生成：传入最小协议 XML，运行扫描器生成 .cpp/.hpp
#      并校验生成文件存在（替代 --help——该工具把参数当 XML 文件
#      路径解析，--help/-h 均返回非零，无法作为可运行性判定）
#   3) 失败区分：仅沙箱 EPERM（exec 被拒绝，stderr 匹配
#      Operation not permitted / Permission denied）时 SKIP 退出 0，
#      其余运行失败一律 FAIL 退出 1（防止损坏产物放行）
#
# 用法：test_hyprwayland-scanner.sh <bin_dir>
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "FAIL: 用法: test_hyprwayland-scanner.sh <bin_dir>" >&2
    exit 1
fi
BIN="$1"
SCANNER="$BIN/hyprwayland-scanner"

if [ ! -x "$SCANNER" ]; then
    echo "FAIL: hyprwayland-scanner 不存在或不可执行: $SCANNER"
    exit 1
fi

SRC_DIR=$(mktemp -d)
trap 'rm -rf "$SRC_DIR"' EXIT
cat > "$SRC_DIR/minimal.xml" <<'EOF'
<protocol name="minimal">
  <interface name="wl_minimal" version="1">
    <request name="destroy" type="destructor"/>
  </interface>
</protocol>
EOF
mkdir -p "$SRC_DIR/out"

# 运行扫描器生成代码（真实可运行性验证）
if ! "$SCANNER" "$SRC_DIR/minimal.xml" "$SRC_DIR/out" 2>"$SRC_DIR/err.log"; then
    ERR="$(cat "$SRC_DIR/err.log" 2>/dev/null || true)"
    case "$ERR" in
        *"Operation not permitted"*|*"Permission denied"*)
            echo "SKIP: hyprwayland-scanner 被沙箱拒绝执行（EPERM 环境限制），产物存在性已验证"
            exit 0
            ;;
        *)
            echo "FAIL: hyprwayland-scanner 运行失败（非沙箱限制）"
            echo "  cmd: $SCANNER minimal.xml out" >&2
            echo "  stderr: $ERR" >&2
            exit 1
            ;;
    esac
fi

# 校验代码生成产物（核心功能验证）
cpp_ok="no"; hpp_ok="no"
[ -f "$SRC_DIR/out/minimal.cpp" ] && cpp_ok="yes"
[ -f "$SRC_DIR/out/minimal.hpp" ] && hpp_ok="yes"
if [ "$cpp_ok" = "no" ] || [ "$hpp_ok" = "no" ]; then
    echo "FAIL: 扫描器退出 0 但未生成代码（minimal.cpp=$cpp_ok, minimal.hpp=$hpp_ok）"
    exit 1
fi

echo "PASS: hyprwayland-scanner 可运行且生成代码（minimal.cpp/minimal.hpp）"
exit 0
