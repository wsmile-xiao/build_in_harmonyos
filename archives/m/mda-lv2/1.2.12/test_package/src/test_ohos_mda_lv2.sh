#!/bin/bash
# test_ohos_mda_lv2.sh — HarmonyOS PC (ohos-aarch64) 专项测试（readelf 部分）
#
# 覆盖 OHOS 平台特性（与 test_ohos_load_all.c 配合）：
#  1. readelf 逐插件校验：ELF64 + AArch64 + NEEDED（libc++_shared.so +
#     libc.so，OHOS 动态链接布局）+ 无 RPATH/RUNPATH（插件由宿主
#     dlopen 显式路径加载，包内 rpath 会破坏部署可移植性）
#  2. dlopen 真实加载全部 36 插件 + 抽样生命周期 → test_ohos_load_all.c
#
# Usage: test_ohos_mda_lv2.sh <bundle-dir>
set -euo pipefail

BUNDLE="${1:-}"
if [ -z "$BUNDLE" ]; then
    echo "ERROR: bundle dir path is required"
    exit 1
fi
if [ ! -d "$BUNDLE" ]; then
    echo "ERROR: bundle dir not found: $BUNDLE"
    exit 1
fi

# readelf 定位：HNP 工具链绝对路径优先，PATH 兜底
# （[ -x ] 只查当前目录；裸 command -v 查 PATH——abiword 先例）
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then
        READELF="$cand"
        break
    fi
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
if [ -z "$READELF" ]; then
    echo "ERROR: readelf not found (HNP toolchain or PATH)"
    exit 1
fi
echo "  [ok] readelf: $READELF"

PASS=0
FAIL=0

echo "== Part 1: readelf ELF64/AArch64/NEEDED/RPATH (all plugins) =="
PLUGINS="Ambience Bandisto BeatBox Combo DX10 DeEss Degrade Delay Detune Dither DubDelay Dynamics EPiano Image JX10 Leslie Limiter Loudness MultiBand Overdrive Piano RePsycho RezFilter RingMod RoundPan Shepard Splitter Stereo SubSynth TalkBox TestTone ThruZero Tracker Transient VocInput Vocoder"
for p in $PLUGINS; do
    SO="$BUNDLE/$p.so"
    if [ ! -f "$SO" ]; then
        echo "  [FAIL] $p.so missing"
        FAIL=$((FAIL + 1))
        continue
    fi
    HDR=$("$READELF" -h "$SO")
    if echo "$HDR" | grep -q "Class:.*ELF64" && echo "$HDR" | grep -q "Machine:.*AArch64"; then
        : # ELF64/AArch64 ok
    else
        echo "  [FAIL] $p.so not ELF64/AArch64"
        echo "$HDR" | grep -E "Class|Machine"
        FAIL=$((FAIL + 1))
        continue
    fi
    DYN=$("$READELF" -d "$SO")
    # NEEDED 必须含 libc++_shared.so 与 libc.so（OHOS C++ 插件布局）
    if echo "$DYN" | grep -q "NEEDED.*libc++_shared.so" && echo "$DYN" | grep -q "NEEDED.*libc.so"; then
        : # NEEDED ok
    else
        echo "  [FAIL] $p.so NEEDED missing libc++_shared.so/libc.so"
        echo "$DYN" | grep NEEDED
        FAIL=$((FAIL + 1))
        continue
    fi
    # RPATH/RUNPATH 必须缺失（宿主显式路径 dlopen；包内 rpath 破坏部署）
    if echo "$DYN" | grep -qE "RPATH|RUNPATH"; then
        echo "  [FAIL] $p.so has RPATH/RUNPATH (breaks relocation portability)"
        echo "$DYN" | grep -E "RPATH|RUNPATH"
        FAIL=$((FAIL + 1))
        continue
    fi
    PASS=$((PASS + 1))
done
echo "  Part 1: $PASS passed, $FAIL failed"

if [ "$FAIL" -gt 0 ]; then
    echo "FAILED: $FAIL plugin(s) failed readelf validation"
    exit 1
fi

echo "PASS: all 36 plugins are ELF64/AArch64, NEEDED=[libc++_shared.so,libc.so], no RPATH/RUNPATH"
exit 0
