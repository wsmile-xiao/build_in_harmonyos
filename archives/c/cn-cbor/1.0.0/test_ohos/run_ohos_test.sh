#!/bin/sh
# test_ohos — cn-cbor 1.0.0 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自测（cbor_test 11 CTEST 用例）与 test_package 消费者用例：
#
#   T1  制品架构审计：libcn-cbor.a 内目标文件为 AArch64（OHOS 目标），
#       头文件/CMake 配置/pkg-config 齐备
#   T2  宿主路径泄漏检查：制品中不得含 /storage、/home、/Users 等宿主绝对路径
#   T3  安装制品真实编译运行：仅用包内公开头文件 + 静态库编译一个 CBOR
#       编码/解码往返程序并在本平台执行，验证编码字节与解码结果
#
# 用法：sh run_ohos_test.sh <已安装包根目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
# 注：刻意保持 'set -u'（而非 -euo pipefail）——本脚本为多检查项汇总
# 脚本，经 chk()/fail 累加器收集全部 T1-T3 结果后再统一退出，任一检查
# 失败不应提前中止其余检查（偏离 code-style §7 安全模式的理由）。
set -u
PKG="${1:-}"
[ -n "$PKG" ] || { echo "usage: $0 <package_root>"; exit 2; }
[ -d "$PKG/lib" ] || { echo "FAIL: package lib/ not found: $PKG"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- cn-cbor 1.0.0 HarmonyOS 专项验证 (package=$PKG) ---"

# T1: AArch64 制品审计
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/ohos-cncbor.XXXXXX" 2>/dev/null || mktemp -d)"
llvm-ar t "$PKG/lib/libcn-cbor.a" >/dev/null 2>&1 && AR="llvm-ar" || AR="ar"
"$AR" x "$PKG/lib/libcn-cbor.a" --output="$TMPD" 2>/dev/null || (cd "$TMPD" && "$AR" x "$PKG/lib/libcn-cbor.a")
found=0; arch_ok=1
# CMake+clang(OHOS) 归档成员名为 *.obj（本包实测），GNU/Makefile 项目为 *.o；
# 两种命名均匹配，避免 glob 落空导致 T1 误判
for f in "$TMPD"/*.obj "$TMPD"/*.o "$TMPD"/*.c.o; do
    [ -e "$f" ] || continue
    found=$((found + 1))
    if ! readelf -h "$f" 2>/dev/null | grep -q "AArch64"; then arch_ok=0; fi
done
# chk 语义：0=通过，1=失败；arch_ok 1=全部 AArch64，0=存在非 AArch64
if [ "$found" -gt 0 ] && [ "$arch_ok" = "1" ]; then
    chk "T1 libcn-cbor.a 目标文件 AArch64 (OHOS armv8) [$found files]" 0
else
    chk "T1 libcn-cbor.a 目标文件 AArch64 (OHOS armv8) [found=$found]" 1
fi
[ -f "$PKG/include/cn-cbor/cn-cbor.h" ] && r=0 || r=1
chk "T1 公开头文件 include/cn-cbor/cn-cbor.h" "$r"
[ -f "$PKG/lib/cmake/cn-cbor/cn-cborConfig.cmake" ] && r=0 || r=1
chk "T1 CMake package 配置 cn-cborConfig.cmake" "$r"
[ -f "$PKG/lib/pkgconfig/cn-cbor.pc" ] && r=0 || r=1
chk "T1 pkg-config cn-cbor.pc" "$r"

# T2: 宿主路径泄漏检查
leak=$(strings "$PKG/lib/libcn-cbor.a" 2>/dev/null | grep -E '/storage/|/home/|/Users/' | head -1)
if [ -n "$leak" ]; then
    echo "  leak: $leak"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 安装制品真实编译运行（公开头 + 静态库，CBOR 往返）
cat > "$TMPD/ohos_roundtrip.c" <<'EOF'
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <cn-cbor/cn-cbor.h>

int main(void) {
    cn_cbor_errback err;
    cn_cbor *map = cn_cbor_map_create(&err);
    cn_cbor *v = cn_cbor_int_create(7, &err);
    if (!map || !v || !cn_cbor_mapput_string(map, "n", v, &err)) {
        fprintf(stderr, "build failed\n"); return 1;
    }
    uint8_t buf[32];
    ssize_t n = cn_cbor_encoder_write(buf, 0, sizeof(buf), map);
    /* {"n": 7} -> a1 61 6e 07 */
    if (n != 4 || buf[0] != 0xa1 || buf[1] != 0x61 || buf[2] != 'n' || buf[3] != 0x07) {
        fprintf(stderr, "encode mismatch: %zd\n", n); return 1;
    }
    cn_cbor *dec = cn_cbor_decode(buf, (size_t)n, &err);
    cn_cbor *g = dec ? cn_cbor_mapget_string(dec, "n") : NULL;
    if (!g || g->type != CN_CBOR_UINT || g->v.uint != 7) {
        fprintf(stderr, "decode mismatch\n"); return 1;
    }
    printf("OHOS round-trip OK: {n:7} -> a1 61 6e 07 -> 7\n");
    cn_cbor_free(dec);
    cn_cbor_free(map);
    return 0;
}
EOF
/bin/sh -c "clang -I\"$PKG/include\" \"$TMPD/ohos_roundtrip.c\" \"$PKG/lib/libcn-cbor.a\" -o \"$TMPD/ohos_rt\"" >/dev/null 2>&1
if [ -x "$TMPD/ohos_rt" ]; then
    out=$("$TMPD/ohos_rt" 2>&1); rc=$?
    echo "  $out"
    chk "T3 安装制品编译运行 CBOR 往返 (exit=$rc)" "$rc"
else
    echo "  compile failed"
    chk "T3 安装制品编译运行 CBOR 往返" 1
fi

rm -rf "$TMPD"
echo "--- cn-cbor OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail