#!/bin/sh
# test.sh — ccache 4.14 消费者用例（R34）
# 模拟上层业务组件调用已安装 ccache 公开 CLI，验证真实缓存语义：
# 编译同一 C 源两次，第一次 cache_miss、第二次 cache_hit。
set -e

echo "--- ccache consumer test ---"
ccache --version | head -1
echo "DBG: ccache=$(command -v ccache) CCACHE_DIR=${CCACHE_DIR:-unset}"
ccache --show-config 2>&1 | grep -iE "cache_dir|disable" | head -3

# 编译器解析（conanrun 环境可能不含系统 PATH 中的 clang）
if command -v clang >/dev/null 2>&1; then
    COMPILER=clang
elif [ -x /data/service/hnp/bin/clang ]; then
    COMPILER=/data/service/hnp/bin/clang
else
    echo "CONSUMER_FAIL: no clang compiler found"
    exit 1
fi

rm -rf ccache_test_cache _tp.c _tp1.o _tp2.o
echo 'int main(void){return 42;}' > _tp.c
export CCACHE_DIR="$PWD/ccache_test_cache"
# W3/CI 工作环境可能注入 CCACHE_DISABLE 禁用 ccache 缓存；消费者用例必须
# 验证真实缓存语义，显式解除环境禁用
unset CCACHE_DISABLE 2>/dev/null || true

ccache "$COMPILER" -c _tp.c -o _tp1.o 2>"$PWD/compile1.err" || { echo "COMPILE1_FAIL: $(cat "$PWD/compile1.err" | head -3)"; exit 1; }
miss=$(ccache --show-stats | awk '/^ *Misses:/ {print $2; exit}')
ccache "$COMPILER" -c _tp.c -o _tp2.o 2>"$PWD/compile2.err" || { echo "COMPILE2_FAIL: $(cat "$PWD/compile2.err" | head -3)"; exit 1; }
hit=$(ccache --show-stats | awk '/^ *Hits:/ {print $2; exit}')

echo "miss=$miss hit=$hit"
if [ "$miss" = "1" ] && [ "$hit" = "1" ]; then
    echo "CONSUMER_CACHE_OK"
else
    echo "CONSUMER_FAIL miss=$miss hit=$hit"
    exit 1
fi
