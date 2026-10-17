#!/usr/bin/env bash
# test_package/ohos_specific_test.sh
# HarmonyOS(OpenHarmony PC / aarch64) 专项测试 for vosk-api 0.3.50.
#
# 覆盖的 OHOS 平台特性：
#   1. 目标架构产物：libvosk.so 必须是 64 位 AArch64 ELF —— 证明用的是
#      aarch64-linux-ohos 工具链（设备原生 clang 15），而非宿主架构。
#   2. 动态依赖闭合：NEEDED 必须恰好是本平台可解析的库（libc++_shared.so /
#      libc.so / libopenblas.so.0，均为 OHOS 侧存在的依赖），不得出现绝对路径
#      NEEDED（构建机路径泄漏）。
#   3. 运行期符号可见性：OHOS 的 musl 动态加载器下 dlopen(libvosk.so) 必须成功，
#      且公开 C API 符号可从 .so 的 dynsym 解析 —— 这正是 Python ctypes /
#      Java / C# 绑定消费 libvosk.so 的方式（不链接、只 dlopen）。
#
# 全部为真实命令、真实退出码、真实可观测结果。
set -u

LIB="$1"
PROBE="$2"
WORK="$3"
LOG="${4:-}"

if [ -z "${LIB:-}" ] || [ -z "${PROBE:-}" ] || [ -z "${WORK:-}" ]; then
    echo "Usage: $0 <libvosk.so> <ohos_dlopen_probe> <work_dir> [log_file]"
    exit 1
fi

mkdir -p "$WORK"
LOG="${LOG:-$WORK/ohos_specific_test.log}"

run_checks() {
    pass=0
    fail=0

    report() { # report <ok|bad> <message>
        if [ "$1" = "ok" ]; then
            echo "PASS: $2"
            pass=$((pass + 1))
        else
            echo "FAIL: $2"
            fail=$((fail + 1))
        fi
    }

    echo "=== [OHOS专项] vosk-api 0.3.50 HarmonyOS test ==="
    echo "lib:   $LIB"
    echo "probe: $PROBE"
    echo "work:  $WORK"
    echo "uname: $(uname -srm 2>/dev/null || echo unknown)"

    READER=""
    for cand in readelf llvm-readelf; do
        if command -v "$cand" >/dev/null 2>&1; then READER="$cand"; break; fi
    done

    echo
    echo "--- Test A: 64-bit AArch64 ELF target (鸿蒙 PC 原生架构) ---"
    if [ -n "$READER" ]; then
        "$READER" -h "$LIB" > "$WORK/readelf-header.txt" 2>&1 || true
        sed 's/^/  /' "$WORK/readelf-header.txt"
        if grep -q "Machine:.*AArch64" "$WORK/readelf-header.txt"; then
            report ok "libvosk.so ELF machine is AArch64"
        else
            report bad "libvosk.so ELF machine is not AArch64"
        fi
        if grep -q "Class:.*ELF64" "$WORK/readelf-header.txt"; then
            report ok "libvosk.so ELF class is 64-bit"
        else
            report bad "libvosk.so is not a 64-bit ELF"
        fi
    else
        report bad "no ELF reader (readelf/llvm-readelf) available"
    fi

    echo
    echo "--- Test B: dynamic dependency closure (OHOS resolvable NEEDED) ---"
    if [ -n "$READER" ]; then
        "$READER" -d "$LIB" 2>/dev/null | grep "NEEDED" > "$WORK/needed.txt" || true
        sed 's/^/  /' "$WORK/needed.txt"

        for dep in "libc++_shared.so" "libc.so" "libopenblas.so.0"; do
            if grep -q "\[$dep\]" "$WORK/needed.txt"; then
                report ok "NEEDED declares $dep"
            else
                report bad "NEEDED is missing $dep"
            fi
        done

        # 绝对路径 NEEDED（如 /storage/.../libfoo.so）= 构建机路径泄漏
        if grep -E "NEEDED.*\[/" "$WORK/needed.txt" | grep -q .; then
            grep -E "NEEDED.*\[/" "$WORK/needed.txt" | sed 's/^/  /'
            report bad "NEEDED contains build-machine absolute paths"
        else
            report ok "NEEDED has no build-machine absolute paths"
        fi
    else
        report bad "no ELF reader available for NEEDED inspection"
    fi

    echo
    echo "--- Test C: runtime dlopen through the OHOS loader (musl ldso) ---"
    "$PROBE" "$LIB" > "$WORK/dlopen-probe.txt" 2>&1
    probe_rc=$?
    sed 's/^/  /' "$WORK/dlopen-probe.txt"
    if [ "$probe_rc" -eq 0 ]; then
        report ok "dlopen(libvosk.so) succeeds and all public C API symbols resolve"
    else
        report bad "dlopen/dlsym probe failed (rc=$probe_rc)"
    fi

    echo
    echo "=== summary: pass=$pass fail=$fail ==="
}

run_checks > "$LOG" 2>&1
cat "$LOG"

summary_line=$(grep "^=== summary:" "$LOG" | tail -1)
echo "ohos_specific_test: ${summary_line:-no summary} (log: $LOG)"

if grep -q "^FAIL:" "$LOG"; then
    exit 1
fi
exit 0
