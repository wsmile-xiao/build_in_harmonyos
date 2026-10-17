#!/usr/bin/env bash
# zipinfo smoke test: 使用包内 zipinfo 二进制验证安装产物
# 用法: test.sh <package_bin_dir>
# 必须使用 package_folder 中的二进制（而非系统 PATH），
# 否则 L1e 负向测试（sabotage 包产物后重跑）会判定为 fake test。
set -e

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "zipinfo: package bin dir not found: $BIN_DIR"
    exit 1
fi

ZIPINFO="$BIN_DIR/zipinfo"
if [ ! -x "$ZIPINFO" ]; then
    echo "zipinfo: binary missing in package: $ZIPINFO"
    exit 1
fi

echo "zipinfo: using package binary at $ZIPINFO"

# 1) 版本检查（zipinfo 无 --version，用 -v 输出版本信息）
VERSION_OUT="$("$ZIPINFO" -v 2>&1)" || {
    echo "zipinfo: -v failed"
    exit 1
}
echo "zipinfo: -v -> $(echo "$VERSION_OUT" | head -1)"

# 2) 功能验证: 用 zipinfo 列出 zip 内容（读取链路）
#    借用 Info-ZIP 自带测试归档或临时构造 zip
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
if [ -f /storage/Users/currentUser/build_in_harmonyos/archives/z/zipinfo/6.0.2/../unzip60/testmake.zip ] 2>/dev/null; then
    ZIP_SRC="/storage/Users/currentUser/build_in_harmonyos/archives/z/zipinfo/6.0.2/../unzip60/testmake.zip"
else
    # 无测试归档时用 python zipfile 构造一个
    python3 - "$TMPD/make.zip" <<'PYEOF'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("hello.txt", "zipinfo smoke test\n")
PYEOF
    ZIP_SRC="$TMPD/make.zip"
fi

LIST_OUT="$("$ZIPINFO" "$ZIP_SRC" 2>&1)" || {
    echo "zipinfo: listing failed: $LIST_OUT"
    exit 1
}
if ! echo "$LIST_OUT" | grep -qE "hello\.txt|testmake|file"; then
    echo "zipinfo: unexpected listing output: $LIST_OUT"
    exit 1
fi
echo "zipinfo: listing OK"

echo "zipinfo test_package: PASS"
