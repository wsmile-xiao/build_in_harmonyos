#!/bin/sh
# alex4 1.1 test_package 测试源文件（L0c 门禁识别 .sh）。
# 消费测试：bin/alex4 存在且为 ELF 可执行文件 + 数据文件（alex4.ini/data.dat/maps.dat）。
# 用法：sh test_alex4.sh <package bin 目录> <package share 目录>
set -u
BIN="${1:?usage: test_alex4.sh <bin dir> <share dir>}"
SHARE="${2:?usage: test_alex4.sh <bin dir> <share dir>}"
FAIL=0

# 1) bin/alex4 存在
[ -f "$BIN/alex4" ] || { echo "FAIL: missing $BIN/alex4"; FAIL=1; }

# 2) ELF magic 检查（headless 无 file 命令，用 od 读 magic）
if [ -f "$BIN/alex4" ]; then
    magic=$(od -An -tx1 -N4 "$BIN/alex4" 2>/dev/null | tr -d ' \n')
    [ "$magic" = "7f454c46" ] || { echo "FAIL: alex4 not ELF (magic=$magic)"; FAIL=1; }
fi

# 3) 数据文件
for f in alex4.ini; do
    [ -f "$SHARE/$f" ] || { echo "FAIL: missing $SHARE/$f"; FAIL=1; }
done
for f in data.dat maps.dat; do
    [ -f "$SHARE/data/$f" ] || { echo "FAIL: missing $SHARE/data/$f"; FAIL=1; }
done

if [ "$FAIL" -eq 1 ]; then echo "FAIL: alex4 test_package check failed"; exit 1; fi
echo "OK: alex4 test_package passed ($BIN, $SHARE)"
exit 0
