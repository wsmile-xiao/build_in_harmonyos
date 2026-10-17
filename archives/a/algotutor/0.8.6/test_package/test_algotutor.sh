#!/bin/sh
# algotutor 0.8.6 test_package 测试源文件（L0c 门禁识别 .sh）。
# 消费测试：验证安装布局 + perl -c 语法检查不依赖 Tk 的算法模块 + data/*.gr 数据文件。
# 用法：sh test_algotutor.sh <package bin 目录>
# set -eu: 未定义变量/命令失败即退出（aireview P3）；perl -c 失败由显式检查处理
set -eu
BIN="${1:?usage: test_algotutor.sh <package bin dir>}"
FAIL=0

# 1) 安装布局
for f in algotutor utilalgo basic.pl; do
    [ -f "$BIN/$f" ] || { echo "FAIL: missing $BIN/$f"; FAIL=1; }
done
for d in dp graph cgeom data; do
    [ -d "$BIN/$d" ] || { echo "FAIL: missing dir $BIN/$d"; FAIL=1; }
done

# 2) perl -c 语法检查不依赖 Tk 的模块
for m in basic.pl Graph.pm BST.pm Heap.pm Vector2.pm Configurable.pm; do
    [ -f "$BIN/$m" ] || { echo "FAIL: missing module $BIN/$m"; FAIL=1; continue; }
    out=$(perl -c -I "$BIN" "$BIN/$m" 2>&1)
    [ $? -eq 0 ] || { echo "FAIL: perl -c $m: $out"; FAIL=1; }
done

# 3) data/*.gr 数据文件
n=$(ls "$BIN"/data/*.gr 2>/dev/null | wc -l)
[ "$n" -gt 0 ] || { echo "FAIL: no data/*.gr in $BIN/data"; FAIL=1; }

if [ "$FAIL" -eq 1 ]; then echo "FAIL: algotutor test_package check failed"; exit 1; fi
echo "OK: algotutor test_package layout + syntax check passed ($BIN)"
exit 0
