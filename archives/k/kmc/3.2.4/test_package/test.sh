#!/data/service/hnp/bin/bash
# test_package/test.sh — kmc 3.2.4 消费验证（由 conanfile test() 以 bash 调起）
# 用法: test.sh <package_folder> <cxx>
# 注: package_type=static-library 时 VirtualRunEnv 不注入 PATH，工具一律用 $PKG/bin 绝对路径。
set -eu

PKG="$1"
CXX_BIN="${2:-clang++}"
SRC0="$(cd "$(dirname "$0")" && pwd)"          # test.sh 所在目录（cd 之前固化为绝对路径）
FIX="$SRC0/data"                               # 上游 fixture（tests/kmc_CLI/data 同源拷贝）
TMP="$(pwd)/tp-tmp"; rm -rf "$TMP"; mkdir -p "$TMP"

echo "[T1] 鸿蒙特有①: aarch64 NEON 基数排序选路断言 (libkmc_core.a 符号)"
NEON_N=$(nm "$PKG/lib/libkmc_core.a" 2>/dev/null | grep -c 'RadixSortMSD_NEON' || true)
SSE_N=$(nm "$PKG/lib/libkmc_core.a" 2>/dev/null | grep -cE 'RadixSortMSD_SSE' || true)
AVX_N=$(nm "$PKG/lib/libkmc_core.a" 2>/dev/null | grep -cE 'RadixSortMSD_AVX' || true)
if [ "$NEON_N" -le 0 ]; then echo "[T1] FAIL: NEON symbols=$NEON_N (aarch64 选路未生效)"; exit 1; fi
if [ "$SSE_N" -ne 0 ] || [ "$AVX_N" -ne 0 ]; then echo "[T1] FAIL: x86 变体符号泄漏 SSE=$SSE_N AVX=$AVX_N"; exit 1; fi
echo "[T1] PASS: NEON=$NEON_N SSE=$SSE_N AVX=$AVX_N"

echo "[T2] 鸿蒙特有②: OHOS aarch64 ELF 与链接依赖断言"
HDR=$(readelf -h "$PKG/bin/kmc")
echo "$HDR" | grep -q "AArch64" || { echo "[T2] FAIL: 非 AArch64 ELF"; exit 1; }
NEED=$(readelf -d "$PKG/bin/kmc" | grep NEEDED || true)
echo "$NEED" | grep -q "libc\.so" || { echo "[T2] FAIL: 无 libc.so NEEDED"; exit 1; }
if echo "$NEED" | grep -qE "libstdc\+\+|libgcc_s"; then echo "[T2] FAIL: libstdc++/libgcc_s 动态残留: $NEED"; exit 1; fi
echo "[T2] PASS: AArch64 + NEEDED=[$NEED]"

echo "[T3] 上游 fixture 断言复刻: single_read.fq k=28 ci=1 → Total no. of k-mers == 70"
cd "$TMP"
"$PKG/bin/kmc" -k28 -ci1 -jstats.json "$FIX/single_read.fq" 28mers .
N=$(grep '#Total no. of k-mers' stats.json | cut -f 2 -d ':' | cut -f 2 -d ' ' | cut -f 1 -d ',')
[ "$N" = "70" ] || { echo "[T3] FAIL: Total no. of k-mers=$N (期望 70)"; exit 1; }
echo "[T3] PASS: Total no. of k-mers == 70"

echo "[T3b] 上游 fixture 断言复刻: issue-180 dump == pattern.dump"
"$PKG/bin/kmc" -v -k5 -fa -ci1 -t1 "$FIX/issue-180/input.fa" bug-report.kmc .
"$PKG/bin/kmc_dump" bug-report.kmc issue-180.kmers
cmp issue-180.kmers "$FIX/issue-180/pattern.dump"
echo "[T3b] PASS: issue-180.kmers == pattern.dump"

echo "[T4] kmc_tools 转储链路"
"$PKG/bin/kmc_tools" transform 28mers dump 28mers.dump > /dev/null
[ -s 28mers.dump ] || { echo "[T4] FAIL: kmc_tools dump 输出为空"; exit 1; }
echo "[T4] PASS: kmc_tools transform dump 非空"

echo "[T5] KMC::Runner API 消费者 (kmc_runner.h + libkmc_core)"
"$CXX_BIN" -std=c++14 -Wall -I "$PKG/include" "$SRC0/consumer.cpp" \
    -L "$PKG/lib" -lkmc_core -lz -pthread -o consumer_bin
./consumer_bin "$FIX/single_read.fq" "$TMP" "$TMP/api_db"
echo "[T5] PASS: Runner API 消费断言全过"

echo "[test_package] ALL PASS (T1 NEON/ELF 鸿蒙特有 ×2, T3/T3b 上游 fixture ×2, T4 消费链路, T5 API 消费者)"
