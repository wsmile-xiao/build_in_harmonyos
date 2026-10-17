#!/data/service/hnp/bin/bash
# test_package/test.sh — cscope 15.9 冒烟 + 功能测试
# 在 conanrun 环境运行（PATH 含已安装 bin/）
set -euo pipefail

echo "[test] cscope -V"
cscope -V 2>&1
if cscope -V 2>&1 | grep -q "version 15"; then
    echo "✅ -V OK"
else
    echo "❌ cscope -V 未输出版本号"
    exit 1
fi

# 功能测试：对一个小 C 工程建交叉引用库，再用行模式查询符号定义
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cscope-test-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

cat > sample.c <<'EOF'
int target_symbol(int x) { return x + 1; }
int caller(void) { return target_symbol(41); }
EOF

echo "[test] cscope -b（建交叉引用库）"
cscope -b -f cscope.out sample.c
test -s cscope.out || { echo "❌ cscope.out 未生成"; exit 1; }

echo "[test] cscope -d -L -0 target_symbol（行模式查询符号）"
cscope -d -f cscope.out -L -0 target_symbol > out.txt
cat out.txt
if grep -q "target_symbol" out.txt; then
    echo "✅ 功能查询 OK"
else
    echo "❌ 查询未命中 target_symbol"
    exit 1
fi
