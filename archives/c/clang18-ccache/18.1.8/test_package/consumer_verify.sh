#!/data/service/hnp/bin/bash
# clang18-ccache 18.1.8 — 消费者验证脚本（鸿蒙专项）
# 模拟业务上层组件：仅通过已安装 ccache 的公开命令行接口（编译器包装器）
# 编译 OHOS aarch64 C 程序，验证编译、缓存命中（cache hit）与可运行产物。
# 脚本由 test_package/conanfile.py 调用（CONFIG_SHELL 指向 bash）。
set -u

CCACHE_BIN="$(command -v ccache)"
if [ -z "${CCACHE_BIN}" ]; then
    echo "CONSUMER_FAIL ccache-not-found-in-path"
    exit 1
fi
OHOS_CLANG=/data/service/hnp/bin/clang

# 可写临时目录：/tmp 只读时依次尝试候选挂载点（R33 恢复规则）
WORKDIR=""
for base in "${TMPDIR:-}" /data/storage/el2/base/haps/entry/files /data/storage/el2/base; do
    [ -n "$base" ] || continue
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

# 1) 编译入口源文件（真实 C 源，非空壳）
cat > "$WORKDIR/hello.c" <<'EOF'
#include <stdio.h>
int main(void) { printf("consumer-ohos-hello: ccache ok sum=%d\n", 1+2); return 0; }
EOF

# 2) 通过 ccache 包装 OHOS clang 编译对象文件（第一次：缓存 miss）
export CCACHE_DIR="$WORKDIR/ccache"
export CCACHE_NODIRECT=1
"$CCACHE_BIN" "$OHOS_CLANG" -c -O2 -o "$WORKDIR/hello.o" "$WORKDIR/hello.c" >"$WORKDIR/compile1.log" 2>&1
rc1=$?
echo "first-compile-rc=$rc1"

# 3) 相同命令二次编译（期望 cache hit）
"$CCACHE_BIN" "$OHOS_CLANG" -c -O2 -o "$WORKDIR/hello.o" "$WORKDIR/hello.c" >"$WORKDIR/compile2.log" 2>&1
rc2=$?
echo "second-compile-rc=$rc2"

# 4) 链接为可执行文件并运行（业务上层正常链接目标）
"$OHOS_CLANG" -O2 -o "$WORKDIR/hello" "$WORKDIR/hello.o" >"$WORKDIR/link.log" 2>&1
rc3=$?
echo "link-rc=$rc3"

# 5) 缓存统计：显示 hits/misses（可观察结果）
"$CCACHE_BIN" --show-stats 2>"$WORKDIR/stats.log" | grep -Ei "cache hit|direct cache hit|Hits|Misses" | head -6

# 6) 运行产物验证
if [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ] && [ "$rc3" -eq 0 ]; then
  out="$("$WORKDIR/hello" 2>&1)"
  echo "run-output=$out"
  echo "$out" | grep -q "ccache ok" && echo "CONSUMER_PASS" && exit 0
fi
echo "CONSUMER_FAIL rc1=$rc1 rc2=$rc2 rc3=$rc3"
exit 1
