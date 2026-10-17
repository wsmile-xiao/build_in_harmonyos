#!/bin/sh
# gnupg test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_gnupg.sh <pkg_dir>
#
# 校验 gnupg 应用包可运行：
#   ① bin/gpgv 存在 + 可执行 + 真实执行 `gpgv --version` 断言版本号
#   ② bin/gpg  存在 + 可执行 + 真实执行 `gpg  --version` 断言版本号
#
# 说明：gpgv 是 apt Release 签名验证实际使用的工具（本包适配的主因）。
set -eu

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

EXPECT="2.5.22"

for tool in gpgv gpg; do
    BIN="$PKG/bin/$tool"
    if [ ! -f "$BIN" ]; then
        echo "FAIL: bin/$tool missing in $PKG" >&2
        exit 1
    fi
    if [ ! -x "$BIN" ]; then
        echo "FAIL: bin/$tool not executable" >&2
        exit 1
    fi
    # 真实执行并断言版本号（R34：不接受仅存在性断言）
    OUT="$("$BIN" --version 2>&1)" || {
        echo "FAIL: $tool --version 退出非零: $OUT" >&2
        exit 1
    }
    case "$OUT" in
        *"$EXPECT"*) : ;;
        *) echo "FAIL: $tool --version 未报出 $EXPECT: $(echo "$OUT" | head -1)" >&2; exit 1 ;;
    esac
    echo "OK: $tool --version → $(echo "$OUT" | head -1)"
done

echo "gnupg test_package PASS ($EXPECT)"
exit 0
