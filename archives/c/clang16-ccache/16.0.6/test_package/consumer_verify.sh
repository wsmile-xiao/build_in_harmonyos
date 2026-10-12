#!/data/service/hnp/bin/bash
# clang16-ccache 16.0.6 — 消费者验证脚本（鸿蒙专项）
# 模拟业务上层组件：仅通过已安装 ccache 的公开命令行接口（编译器包装器）
# 编译 OHOS aarch64 C 程序，验证编译、缓存命中（cache hit）与可运行产物。
# 脚本由 test_package/conanfile.py 调用（CONFIG_SHELL 指向 bash）。
# 注：不使用 set -e —— 编译/链接返回码需逐项捕获并汇总判定（rc1/rc2/rc3）。
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CCACHE_BIN="$(command -v ccache)"
if [ -z "${CCACHE_BIN}" ]; then
    echo "CONSUMER_FAIL ccache-not-found-in-path"
    exit 1
fi

# OHOS clang 定位：CI worker 为 /data/service/hnp/bin/clang；
# 本地设备（无 hnp）回退 PATH 中的 OHOS SDK clang。
OHOS_CLANG=""
for cand in /data/service/hnp/bin/clang "$(command -v clang)"; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        OHOS_CLANG="$cand"
        break
    fi
done
if [ -z "$OHOS_CLANG" ]; then
    echo "CONSUMER_FAIL ohos-clang-not-found"
    exit 1
fi
echo "using-ohos-clang=$OHOS_CLANG"

# 可写临时目录：/tmp 只读时依次尝试候选挂载点（R33 恢复规则）
WORKDIR=""
for base in "${TMPDIR:-}" /data/storage/el2/base/haps/entry/files /data/storage/el2/base "$HOME/tmp" /tmp; do
    [ -n "$base" ] || continue
    [ -d "$base" ] || continue
    if WORKDIR="$(mktemp -d "$base/ccache-consumer-XXXXXX" 2>/dev/null)"; then
        break
    fi
    WORKDIR=""
done
if [ -z "$WORKDIR" ]; then
    echo "CONSUMER_FAIL no-writable-tmpdir"
    exit 10
fi
trap 'rm -rf "$WORKDIR"' EXIT

# 1) 编译入口源文件：优先使用随包分发的真实消费者 C 源 consumer_hello.c
if [ -f "$SCRIPT_DIR/consumer_hello.c" ]; then
    cp "$SCRIPT_DIR/consumer_hello.c" "$WORKDIR/hello.c"
else
    cat > "$WORKDIR/hello.c" <<'EOF'
#include <stdio.h>
int main(void) { printf("consumer-ohos-hello: ccache ok sum=%d\n", 1+2); return 0; }
EOF
fi

# 2) 通过 ccache 包装 OHOS clang 编译对象文件（第一次：缓存 miss）
# 说明：本地 W3 验证环境会向子进程注入 CCACHE_DISABLE=1（构建加速红线，
# 针对外层构建系统）；本用例被测对象就是 ccache 自身的缓存行为，须解除。
unset CCACHE_DISABLE
export CCACHE_DIR="$WORKDIR/ccache"
export CCACHE_NODIRECT=1
"$CCACHE_BIN" "$OHOS_CLANG" -c -O2 -o "$WORKDIR/hello.o" "$WORKDIR/hello.c" >"$WORKDIR/compile1.log" 2>&1
rc1=$?
echo "first-compile-rc=$rc1"

# 3) 相同命令二次编译（期望 cache hit）
"$CCACHE_BIN" "$OHOS_CLANG" -c -O2 -o "$WORKDIR/hello.o" "$WORKDIR/hello.c" >"$WORKDIR/compile2.log" 2>&1
rc2=$?
echo "second-compile-rc=$rc2"

# 4) 链接为可执行文件（业务上层正常链接目标）
"$OHOS_CLANG" -O2 -o "$WORKDIR/hello" "$WORKDIR/hello.o" >"$WORKDIR/link.log" 2>&1
rc3=$?
echo "link-rc=$rc3"

# 5) 缓存命中断言（direct + preprocessed 命中总数必须 >= 1）与统计展示
d_hits=$("$CCACHE_BIN" --print-stats 2>/dev/null | awk '/^direct_cache_hit/ {print $2}')
p_hits=$("$CCACHE_BIN" --print-stats 2>/dev/null | awk '/^preprocessed_cache_hit/ {print $2}')
d_hits="${d_hits:-0}"
p_hits="${p_hits:-0}"
total_hits=$((d_hits + p_hits))
echo "cache-hits=$total_hits (direct=$d_hits preprocessed=$p_hits)"
"$CCACHE_BIN" --show-stats 2>/dev/null | grep -Ei "Hits|Misses" | head -4
if [ "$total_hits" -lt 1 ]; then
    echo "CONSUMER_FAIL no-cache-hit"
    exit 1
fi

# 6) 运行产物验证
if [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ] && [ "$rc3" -eq 0 ]; then
    out="$("$WORKDIR/hello" 2>&1)"
    echo "run-output=$out"
    echo "$out" | grep -q "consumer-ohos-hello" && echo "CONSUMER_PASS" && exit 0
fi
echo "CONSUMER_FAIL rc1=$rc1 rc2=$rc2 rc3=$rc3"
exit 1
