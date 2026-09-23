#!/usr/bin/env bash
# test_package/test.sh — nsnake 3.0.1.1 冒烟 + 打包完整性核对
# 用法: bash test.sh [package_folder]   （不给参数时依赖 PATH 上的 nsnake）
set -euo pipefail

PKG="${1:-}"
BIN="${PKG:+$PKG/bin/nsnake}"
BIN="${BIN:-nsnake}"

"$BIN" --version | grep -q 'nsnake v'
echo "[ok] nsnake --version"

if [ -n "$PKG" ]; then
    LV="$PKG/share/games/nsnake/levels"
    [ -d "$LV" ] || { echo "[fail] 关卡目录缺失: $LV"; exit 1; }
    levels=$(find "$LV" -name '*.nsnake' | wc -l)
    [ "$levels" -eq 31 ] || { echo "[fail] 关卡数 $levels != 31"; exit 1; }
    echo "[ok] 31 个关卡已入包"

    for f in share/man/man6/nsnake.6 share/pixmaps/nsnake.xpm \
             share/applications/nsnake.desktop \
             share/icons/hicolor/16x16/apps/nsnake.png \
             share/icons/hicolor/32x32/apps/nsnake.png; do
        [ -s "$PKG/$f" ] || { echo "[fail] 缺数据文件或为空: $f"; exit 1; }
    done
    echo "[ok] man6 / pixmaps / desktop / icons 均已入包且非空"

    # 注意：不能用 `! grep ...`——bash 的 errexit 显式豁免被 `!` 反转的命令，
    # 那样占位符残留时脚本仍会以 0 退出。必须写成显式 if 分支才能被 CI 捕获。
    if grep -qE '\b(VERSION|DATE)\b' "$PKG/share/man/man6/nsnake.6"; then
        echo "[fail] man6 仍含 VERSION/DATE 占位符"; exit 1
    fi
    echo "[ok] man6 占位符已替换"
fi

echo "[ok] nsnake smoke + packaging test passed"
