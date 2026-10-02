#!/bin/bash
# test_package/test.sh — weggli 0.2.4 consumer smoke test + HarmonyOS-specific cases.
#
# 5 消费者用例（上游 CLI 语义）+ 3 项鸿蒙特有用例（H1 ELF 目标架构、H2 SIGPIPE
# 重置路径、H3 鸿蒙专属样例语义查询）。所有用例真实执行已打包的 weggli 二进制，
# 计数取自本脚本的实际执行结果，并输出 HMBS_TEST_PACKAGE_RESULT 标记。
#
# 注意（OHOS 平台）：/tmp 只读，临时文件一律落在 ${TMPDIR:-$HOME/tmp}。
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
WEGGLI="$(command -v weggli || true)"
if [ -z "$WEGGLI" ]; then
    echo "FAIL - packaged weggli binary not found on PATH" >&2
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-$HOME/tmp}/weggli-tp.XXXXXX")" || exit 1
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

echo "weggli binary: ${WEGGLI}"
"${WEGGLI}" --version > "${WORK}/version.out" 2> "${WORK}/version.err"
record "C1 version" 0 $? "${WORK}/version.out" "weggli 0.2.4"

"${WEGGLI}" --help > "${WORK}/help.out" 2> "${WORK}/help.err"
record "C2 usage/help" 0 $? "${WORK}/help.out" "USAGE"

"${WEGGLI}" -u '{_ $buf[_]; memcpy($buf,_,_);}' \
    "${HERE}/fixtures/ohos_sample.c" > "${WORK}/c.out" 2> "${WORK}/c.err"
record "C3 C semantic query (stack buffer memcpy)" 0 $? "${WORK}/c.out" \
    "copy_ohos_payload"

"${WEGGLI}" -X -u '{for (_ $v : _) { _; }}' \
    "${HERE}/fixtures/ohos_sample.cpp" > "${WORK}/cpp.out" 2> "${WORK}/cpp.err"
record "C4 C++ semantic query (range-for + lambda)" 0 $? "${WORK}/cpp.out" \
    "sum_ohos_values"

"${WEGGLI}" '{foo' "${HERE}/fixtures/ohos_sample.c" \
    > "${WORK}/bad.out" 2> "${WORK}/bad.err"
record "C5 invalid pattern error path" 1 $? "${WORK}/bad.err" \
    "Query parsing failed"

# ── HarmonyOS-specific cases ─────────────────────────────────────────
# H1: 打包产物必须是 OHOS armv8（aarch64）目标的可执行 ELF
readelf -h "${WEGGLI}" > "${WORK}/elf.out" 2> "${WORK}/elf.err"
record "H1 OHOS target artifact (AArch64 ELF)" 0 $? "${WORK}/elf.out" \
    "AArch64"

# H2: 本次 OHOS 适配点（nix signal → SIGPIPE 默认处理）在鸿蒙运行时生效：
#     stdout 提前关闭时进程以 SIGPIPE(141) 结束，而不是 Rust panic(101)。
{
    i=0
    while [ "$i" -lt 3000 ]; do
        echo "int f${i}(void) { char buf[10]; return buf[$((i % 10))]; }"
        i=$((i + 1))
    done
} > "${WORK}/sigpipe_big.c"
"${WEGGLI}" -u 'char $buf[10];' "${WORK}/sigpipe_big.c" \
    2> "${WORK}/sigpipe.err" | head -n 1 > "${WORK}/sigpipe.out"
SIGPIPE_RC="${PIPESTATUS[0]}"
TOTAL=$((TOTAL + 1))
if { [ "${SIGPIPE_RC}" -eq 141 ] || [ "${SIGPIPE_RC}" -eq 0 ]; } \
    && ! grep -qi "panicked" "${WORK}/sigpipe.err"; then
    PASS=$((PASS + 1))
    echo "ok   [H2 SIGPIPE reset on OHOS] weggli_rc=${SIGPIPE_RC} (SIGPIPE=141, no panic)"
else
    FAIL=$((FAIL + 1))
    echo "FAIL [H2 SIGPIPE reset on OHOS] weggli_rc=${SIGPIPE_RC}"
    sed -n '1,5p' "${WORK}/sigpipe.err"
fi

# H3: 鸿蒙专属样例（符号名 OHOS_PC_UPSTREAM_sample）端到端语义查询命中
"${WEGGLI}" -u 'OHOS_PC_UPSTREAM_sample(_)' "${HERE}/fixtures" \
    > "${WORK}/ohos.out" 2> "${WORK}/ohos.err"
record "H3 HarmonyOS sample semantic query" 0 $? "${WORK}/ohos.out" \
    "OHOS_PC_UPSTREAM_sample"

echo "consumer + HarmonyOS cases: passed=${PASS} failed=${FAIL} total=${TOTAL}"
printf 'HMBS_TEST_PACKAGE_RESULT=%s\n' \
    "{\"status\":\"$([ "${FAIL}" -eq 0 ] && echo passed || echo failed)\",\"framework\":\"bash\",\"command\":\"test.sh\",\"discovered\":${TOTAL},\"executed\":${TOTAL},\"passed\":${PASS},\"failed\":${FAIL},\"skipped\":0}"

[ "${FAIL}" -eq 0 ] || exit 1
