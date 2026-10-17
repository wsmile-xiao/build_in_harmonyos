#!/bin/sh
# test_ohos — ccache 4.14 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对 ccache 可执行文件做独立专项检查，
# 区别于上游内置自测（unittest + test/suites）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  --version 输出核验（消费者可见的版本信息）
#   T4  真实缓存语义验证：用 OHOS clang 编译同一 C 源两次，
#       第一次 cache_miss、第二次 cache_hit，证明缓存可真实命中
#       （不只打印字符串，验证业务公开功能的可观察结果）
#
# 用法：sh run_ohos_test.sh <已安装 ccache 二进制路径>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <ccache-binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- ccache HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage/Users、/home、/Users 绝对路径不得进入产物；
# 相对源码路径如 src/ccache/storage/ 属源码目录名，非泄漏）
if strings "$BIN" | grep -qE '/storage/Users/|/home/|/Users/|tmp/builds'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/Users/|/home/|/Users/|tmp/builds' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: --version 输出核验
VER="$("$BIN" --version 2>&1 | head -1)"
echo "$VER" | grep -q "ccache version 4.14" && r=0 || r=1
chk "T3 --version (got: $VER)" "$r"

# T4: 真实缓存语义（clang 编译两次：miss -> hit）
CCACHE_BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"
CACHE_DIR="$(mktemp -d)"
SRC_DIR="$(mktemp -d)"
echo 'int main(void){return 42;}' > "$SRC_DIR/prog.c"
export CCACHE_DIR="$CACHE_DIR"

"$CCACHE_BIN" /data/service/hnp/bin/clang -c "$SRC_DIR/prog.c" -o "$SRC_DIR/prog1.o" 2>"$SRC_DIR/e1" || r=1
MISS=$("$CCACHE_BIN" --show-stats 2>/dev/null | awk '/^ *Misses:/ {print $2; exit}')
"$CCACHE_BIN" /data/service/hnp/bin/clang -c "$SRC_DIR/prog.c" -o "$SRC_DIR/prog2.o" 2>"$SRC_DIR/e2" || r=1
HIT=$("$CCACHE_BIN" --show-stats 2>/dev/null | awk '/^ *Hits:/ {print $2; exit}')
if [ "$MISS" = "1" ] && [ "$HIT" = "1" ]; then
    chk "T4 缓存语义 (miss=$MISS hit=$HIT)" 0
else
    echo "  miss=$MISS hit=$HIT stderr1=$(cat "$SRC_DIR/e1" | head -1) stderr2=$(cat "$SRC_DIR/e2" | head -1)"
    chk "T4 缓存语义 (miss=$MISS hit=$HIT)" 1
fi
rm -rf "$CACHE_DIR" "$SRC_DIR"

if [ "$fail" = "0" ]; then
    echo "ALL OHOS TESTS PASSED"
else
    echo "OHOS TESTS FAILED"
fi
exit "$fail"
