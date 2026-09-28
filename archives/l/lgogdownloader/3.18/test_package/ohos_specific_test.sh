#!/usr/bin/env bash
# test_package/ohos_specific_test.sh
# HarmonyOS(OpenHarmony PC / aarch64) 专项测试 for lgogdownloader 3.18.
#
# 覆盖的 OHOS 平台特性：
#   1. 目标架构产物：可执行文件必须是 64 位 AArch64 ELF（鸿蒙 PC 原生目标），
#      证明交叉编译使用的是 aarch64-linux-ohos 工具链而非宿主架构。
#   2. 平台识别落地：上游 CMakeLists 把 ${CMAKE_SYSTEM_NAME} 编进默认
#      User-Agent。鸿蒙构建必须得到 "HarmonyOS"（而非 "Linux"），
#      因此 `--help` 中 --user-agent 的默认值应包含 "(HarmonyOS"。
#   3. XDG/HOME 路径解析：鸿蒙 /tmp 只读（E002），且 HOME 位于沙箱
#      （/data/storage/el2/base/haps/entry/files）。工具必须能够依据
#      $XDG_CONFIG_HOME/$XDG_CACHE_HOME 在可写目录下创建自身配置树，
#      而不是依赖固定 /tmp 或 /usr 路径。
#
# 全部为真实命令、真实退出码、真实可观测结果。
set -euo pipefail

BIN="$1"
WORK="$2"
LOG="${3:-}"

if [ -z "${BIN:-}" ] || [ -z "${WORK:-}" ]; then
    echo "Usage: $0 <lgogdownloader_binary> <work_dir> [log_file]"
    exit 1
fi

mkdir -p "$WORK"
LOG="${LOG:-$WORK/ohos_specific_test.log}"
fail=0

{
echo "=== [OHOS专项] lgogdownloader 3.18 HarmonyOS test, $(date -Is) ==="
echo "binary: $BIN"
echo "work dir: $WORK"
echo "executor uid: $(python3 -c 'import os;print(os.geteuid())' 2>/dev/null || echo unknown)"
echo "uname: $(uname -srm 2>/dev/null || echo unknown)"

echo
echo "--- Test A: 64-bit AArch64 ELF target (鸿蒙 PC 原生架构) ---"
have=0
if command -v readelf >/dev/null 2>&1; then
    readelf -h "$BIN" > "$WORK/readelf.txt" 2>&1 || true
    sed 's/^/  /' "$WORK/readelf.txt"
    if grep -q "Machine:.*AArch64" "$WORK/readelf.txt"; then
        echo "PASS: ELF machine is AArch64"
        have=1
    else
        echo "FAIL: ELF machine is not AArch64"
        fail=1
    fi
    if grep -q "Class:.*ELF64" "$WORK/readelf.txt"; then
        echo "PASS: ELF class is 64-bit"
    else
        echo "FAIL: ELF is not 64-bit"
        fail=1
    fi
elif command -v file >/dev/null 2>&1; then
    fdesc=$(file "$BIN" 2>/dev/null || true)
    echo "  file: $fdesc"
    if printf '%s' "$fdesc" | grep -Eqi "ELF 64-bit.*(aarch64|arm64)"; then
        echo "PASS: ELF 64-bit aarch64 (via file)"
        have=1
    else
        echo "FAIL: not an ELF 64-bit aarch64 binary"
        fail=1
    fi
else
    echo "FAIL: neither readelf nor file available to verify the ELF target"
    fail=1
fi
[ $have -eq 1 ] || echo "WARN: ELF identity could not be fully confirmed"

echo
echo "--- Test B: HarmonyOS platform baked into the default User-Agent ---"
help=$("$BIN" --help)
ua_line=$(printf '%s\n' "$help" | grep -- "--user-agent" || true)
echo "help: $ua_line"
if printf '%s' "$ua_line" | grep -q "(HarmonyOS"; then
    echo "PASS: CMake detected the OHOS platform name (HarmonyOS) at configure time"
else
    echo "FAIL: default user agent does not carry the HarmonyOS platform id"
    fail=1
fi

echo
echo "--- Test C: XDG_CONFIG_HOME/XDG_CACHE_HOME resolution on OHOS ---"
cfg="$WORK/xdg-config"
cache="$WORK/xdg-cache"
home="$WORK/xdg-home"
# Explicit safety net: rm -rf may only ever touch paths nested under $WORK.
for d in "$cfg" "$cache" "$home"; do
    case "$d" in
        "${WORK%/}"/*) ;;
        *) echo "FAIL: refusing to rm -rf unexpected path '$d'"; exit 1 ;;
    esac
done
rm -rf -- "$cfg" "$cache" "$home"
mkdir -p "$cfg" "$cache" "$home"
rc=0
out=$(HOME="$home" XDG_CONFIG_HOME="$cfg" XDG_CACHE_HOME="$cache" "$BIN" 2>&1) || rc=$?
echo "stdout+stderr:"
printf '%s\n' "$out" | sed 's/^/  /'
echo "exit=$rc"
if [ -f "$cfg/lgogdownloader/cookies.txt" ] && [ -d "$cache/lgogdownloader" ]; then
    echo "PASS: config/cache tree created under XDG dirs (config=$cfg, cache=$cache)"
else
    echo "FAIL: config/cache tree was not created under the XDG dirs"
    fail=1
fi
if printf '%s' "$out" | grep -q "$cfg/lgogdownloader"; then
    echo "PASS: reported config path honors XDG_CONFIG_HOME"
else
    echo "FAIL: reported config path does not honor XDG_CONFIG_HOME"
    fail=1
fi

echo
if [ $fail -ne 0 ]; then
    echo "=== [OHOS专项] lgogdownloader HarmonyOS test FAILED ==="
    exit 1
fi
echo "=== [OHOS专项] lgogdownloader HarmonyOS test PASSED ==="
} 2>&1 | tee "$LOG"

exit "${PIPESTATUS[0]}"
