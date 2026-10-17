#!/bin/bash
# test_package/test.sh — zizmor 1.27.0 consumer smoke test + HarmonyOS-specific cases.
#
# 5 消费者用例（上游 CLI 语义）+ 3 项鸿蒙特有用例（H1 ELF 目标架构、H2 退出路径
# 稳定（jemalloc 移除后的崩溃回归护栏）、H3 鸿蒙专属样例工作流端到端审计）。
# 所有用例真实执行已打包的 zizmor 二进制，计数取自本脚本的实际执行结果，
# 并输出 HMBS_TEST_PACKAGE_RESULT 标记。
#
# 注意（OHOS 平台）：/tmp 只读，临时文件一律落在 ${TMPDIR:-$HOME/tmp}。
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ZIZMOR="$(command -v zizmor || true)"
if [ -z "$ZIZMOR" ]; then
    echo "FAIL - packaged zizmor binary not found on PATH" >&2
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-$HOME/tmp}/zizmor-tp.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT

TOTAL=0
PASS=0
FAIL=0

record() { # name expected_rc actual_rc log_file [required_text]
    local name="$1" expect="$2" rc="$3" log="$4" want="${5:-}"
    TOTAL=$((TOTAL + 1))
    if [ "$rc" -ne "$expect" ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL [${name}] rc=${rc} (expected ${expect})"
        sed -n '1,5p' "$log"
        return
    fi
    if [ -n "$want" ] && ! grep -qF "$want" "$log"; then
        FAIL=$((FAIL + 1))
        echo "FAIL [${name}] missing expected text: ${want}"
        sed -n '1,5p' "$log"
        return
    fi
    PASS=$((PASS + 1))
    echo "ok   [${name}] rc=${rc}"
}

echo "zizmor binary: ${ZIZMOR}"

"${ZIZMOR}" --version > "${WORK}/version.out" 2> "${WORK}/version.err"
record "C1 version" 0 $? "${WORK}/version.out" "zizmor 1.27.0"

"${ZIZMOR}" --help > "${WORK}/help.out" 2> "${WORK}/help.err"
record "C2 usage/help" 0 $? "${WORK}/help.out" "Usage"

# C3: 干净工作流（离线）→ 退出码 0，无发现
"${ZIZMOR}" --no-config --offline --no-progress \
    "${HERE}/fixtures/ohos-clean.yml" > "${WORK}/clean.out" 2> "${WORK}/clean.err"
record "C3 clean workflow audit (offline)" 0 $? "${WORK}/clean.out" \
    "No findings to report"

# C4: 未固定引用的工作流 → zizmor 以发现码退出，并报 unpinned-uses
"${ZIZMOR}" --no-config --offline --no-progress \
    "${HERE}/fixtures/unpinned.yml" > "${WORK}/unpinned.out" 2> "${WORK}/unpinned.err"
record "C4 unpinned uses audit (findings exit code)" 14 $? "${WORK}/unpinned.out" \
    "unpinned-uses"

# C5: SARIF 输出是合法 JSON（消费端集成路径；SARIF 模式固定退出码 0）
"${ZIZMOR}" --no-config --offline --no-progress --format=sarif \
    "${HERE}/fixtures/unpinned.yml" > "${WORK}/sarif.out" 2> "${WORK}/sarif.err"
record "C5 SARIF output" 0 $? "${WORK}/sarif.out" 'sarif-schema-2.1.0.json'

# ── HarmonyOS-specific cases ─────────────────────────────────────────
# H1: 打包产物必须是 OHOS armv8（aarch64）目标的可执行 ELF
readelf -h "${ZIZMOR}" > "${WORK}/elf.out" 2> "${WORK}/elf.err"
record "H1 OHOS target artifact (AArch64 ELF)" 0 $? "${WORK}/elf.out" \
    "AArch64"

# H2: 本次 OHOS 适配点（排除 jemalloc、改用平台分配器）在鸿蒙运行时生效：
#     连续 6 次审计必须全部以退出码 0 结束，且不出现 139(SIGSEGV)。
#     修复前该路径在进程退出时 100% SIGSEGV（含 tokio 运行时析构）。
h2_fail=0
i=0
while [ "$i" -lt 6 ]; do
    "${ZIZMOR}" --no-config --offline --no-progress \
        "${HERE}/fixtures/ohos-clean.yml" > /dev/null 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        h2_fail=$((h2_fail + 1))
        echo "  H2 iteration ${i}: rc=${rc}"
    fi
    i=$((i + 1))
done
TOTAL=$((TOTAL + 1))
if [ "${h2_fail}" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "ok   [H2 stable exit path on OHOS] 6/6 rc=0 (no SIGSEGV)"
else
    FAIL=$((FAIL + 1))
    echo "FAIL [H2 stable exit path on OHOS] ${h2_fail}/6 runs failed"
fi

# H3: 鸿蒙专属样例（工作流含 OHOS_PC_UPSTREAM_sample 标记）端到端审计命中
"${ZIZMOR}" --no-config --offline --no-progress \
    "${HERE}/fixtures/ohos-sample" > "${WORK}/ohos.out" 2> "${WORK}/ohos.err"
record "H3 HarmonyOS sample workflow audit" 14 $? "${WORK}/ohos.out" \
    "ohos-pc-sample.yml"

echo "consumer + HarmonyOS cases: passed=${PASS} failed=${FAIL} total=${TOTAL}"
printf 'HMBS_TEST_PACKAGE_RESULT=%s\n' \
    "{\"status\":\"$([ "${FAIL}" -eq 0 ] && echo passed || echo failed)\",\"framework\":\"bash\",\"command\":\"test.sh\",\"discovered\":${TOTAL},\"executed\":${TOTAL},\"passed\":${PASS},\"failed\":${FAIL},\"skipped\":0}"

[ "${FAIL}" -eq 0 ] || exit 1
