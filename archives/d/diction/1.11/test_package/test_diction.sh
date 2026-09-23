#!/bin/sh
# test_diction.sh — diction 消费者测试（R34：真实执行随包二进制 + 随包短语库）
# 用法: sh test_diction.sh <package_folder>
# 覆盖: 版本输出 / 短语库随包安装 / 默认查找路径的真实短语标记与统计 / 显式
#       短语库路径（上游 test/rundiction 同口径）/ 静默模式
set -e
LC_ALL=C
export LC_ALL

PKG="$1"
BIN="$PKG/bin/diction"
DATA="$PKG/share/diction"

[ -x "$BIN" ] || { echo "FAIL: 未找到可执行文件 $BIN"; exit 1; }
[ -r "$DATA/en" ] || { echo "FAIL: 未找到短语库 $DATA/en"; exit 1; }

echo "[1] diction --version"
"$BIN" --version | grep -q '^GNU diction 1\.11$' || { echo "FAIL: 版本输出不符"; exit 1; }

echo "[2] 默认短语库查找（不传 -f/-n）+ 冗长短语标记"
out=$(printf 'In order to test this, we need a case.\n' | "$BIN" 2>&1)
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q '\[In order to\]' || { echo "FAIL: 未标记 [In order to]"; exit 1; }
printf '%s\n' "$out" | grep -q '\[case\]' || { echo "FAIL: 未标记 [case]"; exit 1; }
printf '%s\n' "$out" | grep -q '2 phrases in 1 sentence found\.' || { echo "FAIL: 统计行不符"; exit 1; }

echo "[3] 显式短语库路径（-f <file> -n，上游 test/rundiction 口径）"
printf 'In order to test this, we need a case.\n' | "$BIN" -f "$DATA/en" -n 2>&1 | grep -q '\[case\]' \
  || { echo "FAIL: 显式短语库未生效"; exit 1; }

echo "[4] 静默模式（-q）"
printf 'In order to test this.\n' | "$BIN" -q >/dev/null

echo "[5] 鸿蒙安装目录迁移后默认查找短语库"
RELOCATED_BASE="${TMPDIR:-$HOME/tmp}"
[ -d "$RELOCATED_BASE" ] || mkdir -p "$RELOCATED_BASE"
RELOCATED="$RELOCATED_BASE/diction-relocated.$$"
trap 'rm -rf "$RELOCATED"' EXIT
cp -R "$PKG" "$RELOCATED"
[ -x "$RELOCATED/bin/diction" ] || { echo "FAIL: 迁移后 diction 不可执行"; exit 1; }
[ -r "$RELOCATED/share/diction/en" ] || { echo "FAIL: 迁移后短语库不存在"; exit 1; }
relocated_out=$(printf 'In order to test this, we need a case.\n' | "$RELOCATED/bin/diction" 2>&1)
printf '%s\n' "$relocated_out"
printf '%s\n' "$relocated_out" | grep -q '\[In order to\]' \
  || { echo "FAIL: 迁移后未使用相对路径短语库"; exit 1; }
printf '%s\n' "$relocated_out" | grep -q '2 phrases in 1 sentence found\.' \
  || { echo "FAIL: 迁移后统计行不符"; exit 1; }

echo "PASS: diction consumer test (5 checks)"
