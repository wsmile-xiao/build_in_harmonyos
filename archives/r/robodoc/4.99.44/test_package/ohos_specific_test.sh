#!/data/service/hnp/bin/bash
# test_package/ohos_specific_test.sh — HarmonyOS-specific adaptation test.
#
# robodoc 是纯 C 程序，其 OHOS 适配集中于"平台识别 + 在鸿蒙文件系统上真实工作"，
# 因此本测试不依赖任何外部样本，全部由脚本自行构造：
#   [case 1] 原生可执行文件：robodoc 是 AArch64 可执行文件，动态链接 OHOS musl
#            （缺失 file/readelf 时记为 SKIP，不判失败）
#   [case 2] 平台三元组：config.guess/config.sub 适配后 configure 识别出
#            aarch64-unknown-linux-ohos（`robodoc --config` 直接回读该宏）
#   [case 3] 真实抽取（HTML）：在 HMDFS 上写出 HTML 文档并校验内容
#   [case 4] 真实抽取（ASCII）：singledoc ASCII 输出校验
#   [case 5] 伴随工具：robohdrs 可运行
#
# 退出码：0 = 全部通过；非 0 = 失败断言数
set -uo pipefail

failures=0
skipped=0

check() {
    # $1 = 描述, $2 = 上一条命令退出码
    if [ "$2" -eq 0 ]; then
        echo "  [PASS] $1"
    else
        echo "  [FAIL] $1"
        failures=$((failures + 1))
    fi
}

work="$(mktemp -d "${TMPDIR:-/tmp}/robodoc-ohos-XXXXXX")"
trap 'rm -rf "${work}"' EXIT
mkdir -p "${work}/src" "${work}/html"

cat > "${work}/src/ohos_probe.c" <<'EOF'
/****f* ohos_probe/robodoc_ohos_probe
 * NAME
 *   robodoc_ohos_probe -- HarmonyOS adaptation probe
 * SYNOPSIS
 *   int robodoc_ohos_probe(void)
 * FUNCTION
 *   Marker symbol used by the HarmonyOS-specific test.
 * SOURCE
 */
int robodoc_ohos_probe(void) { return 42; }
/*******/
EOF

echo "== robodoc HarmonyOS adaptation test =="

# ---------- case 1: native executable ----------
echo "[case 1] native AArch64 executable using the OHOS loader"
robodoc_bin="$(command -v robodoc)"
if command -v readelf >/dev/null 2>&1; then
    readelf -h "${robodoc_bin}" | grep -q "AArch64"
    check "robodoc is an AArch64 ELF" $?
else
    echo "  [SKIP] readelf not available"
    skipped=$((skipped + 1))
fi
if command -v file >/dev/null 2>&1; then
    file "${robodoc_bin}" | grep -q "ld-musl-aarch64"
    check "robodoc links against the OHOS musl loader" $?
else
    echo "  [SKIP] file not available"
    skipped=$((skipped + 1))
fi

# ---------- case 2: HarmonyOS target triplet ----------
echo "[case 2] configure detected the HarmonyOS target triplet"
robodoc --config > "${work}/config.log" 2>&1
check "robodoc --config exits 0" $?
grep -q "Compiled for aarch64-unknown-linux-ohos" "${work}/config.log"
check "config triplet is aarch64-unknown-linux-ohos (config.guess/sub patched)" $?

# ---------- case 3: HTML documentation extraction ----------
echo "[case 3] HTML documentation extraction on HMDFS"
robodoc --src "${work}/src" --doc "${work}/html" --multidoc --html \
        --sections --toc > "${work}/html.log" 2>&1
check "robodoc --html exits 0" $?
grep -q "ohos_probe/robodoc_ohos_probe" "${work}/html/ohos_probe_c.html"
check "generated HTML contains the documented item name" $?
grep -q "return 42;" "${work}/html/ohos_probe_c.html"
check "generated HTML contains the source body" $?

# ---------- case 4: ASCII documentation extraction ----------
echo "[case 4] ASCII documentation extraction"
robodoc --src "${work}/src" --doc "${work}/plain" --singledoc --ascii \
        > "${work}/ascii.log" 2>&1
check "robodoc --ascii exits 0" $?
grep -q "robodoc_ohos_probe -- HarmonyOS adaptation probe" "${work}/plain.txt"
check "ASCII output contains the documentation text" $?

# ---------- case 5: companion tool ----------
echo "[case 5] robohdrs companion tool"
# robohdrs prints its banner to stderr and exits non-zero without arguments;
# capture the output and ignore the exit status (pipefail would otherwise
# mask a successful grep).
robohdrs > "${work}/robohdrs.log" 2>&1 || true
grep -q "robodoc header insertor" "${work}/robohdrs.log"
check "robohdrs prints its banner" $?

echo "== result: $([ "${failures}" -eq 0 ] && echo PASS || echo FAIL) " \
     "(${failures} failure(s), ${skipped} skipped) =="
exit "${failures}"
