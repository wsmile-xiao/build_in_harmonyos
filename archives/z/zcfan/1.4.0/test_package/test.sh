#!/bin/sh
# test_package/test.sh — HarmonyOS consumer smoke test for zcfan 1.4.0.
# Usage: test.sh <bindir>
#
# <bindir> (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the zcfan package_folder.  The package prefix is derived from it
# (<pkg>/bin -> <pkg>) so the man page / license assertions need no extra arg.
#
# Upstream test audit: zcfan 1.4.0 ships NO runtime test suite.  The source
# archive contains only .clang-format, .github/workflows/ci.yml, .gitignore,
# LICENSE, Makefile, README.md, zcfan.1, zcfan.c, zcfan.service.in — there is no
# test/tests directory and the Makefile has no check/test/TESTS target.  Its CI
# runs only static analysis (`make lint`, `make clean clang-tidy`,
# `make clean clang-everything`).  See test_package/MANIFEST.yml for the full
# audit.  The five cases below are NEW HarmonyOS consumer test cases proving
# the packaged OHOS binary actually runs on this platform.
#
# Style: no $(...) command substitution anywhere (OHOS readonly_tmp hardening,
# same convention as vamps 0.99.2) — output capture uses plain redirections
# into $TMPDIR files plus grep/cmp checks.
# `|| true` / `2>/dev/null` are used ONLY on diagnostic commands (echoing the
# captured stdout/stderr of a failing case, listing a directory); their exit
# status never feeds a case verdict — every verdict comes from the recorded rc
# plus grep/cmp/file-existence checks.
set -u
# -e 有意省略：每条用例都要先取 $? 再判定，失败须计数后汇总继续（首轮失败不终止）。
# pipefail 仅在本 shell 支持时启用（POSIX dash 无该选项，CI 的 /bin/sh 可能是 dash，
# 故写成受保护形式，避免在不支持该选项的 shell 上产生噪声/异常）。
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

BINDIR="${1:-}"

# OHOS /tmp is read-only (erofs): prefer the injected writable TMPDIR/TMP/TEMP.
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
# 目录已存在时 mkdir -p 返回 0；失败仅可能因路径不可写，随后写入 $TMPDIR 时会显式
# 暴露（用例判定读的是实际输出文件），故此处忽略返回码不会掩盖真实失败。
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL=5

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream runtime test suite","reason":"zcfan 1.4.0 ships no test/tests directory and no check/test/TESTS target in its Makefile; upstream CI runs only static analysis (make lint, make clean clang-tidy, make clean clang-everything).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":5,"passedCount":0}'
    exit 1
}

echo "[test] zcfan consumer smoke test (bindir='${BINDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "[test] FAIL: bindir not resolved"
    fail
fi

PREFIX="$BINDIR/.."

# ---------------------------------------------------------------- case 1
# The packaged CLI exists and carries the executable bit (the recipe's
# package() chmods 0755 explicitly; a missing artifact aborts the build).
echo "[test] case 1: zcfan_binary_packaged"
if [ -x "$BINDIR/zcfan" ] && [ ! -d "$BINDIR/zcfan" ]; then
    echo "ok: zcfan_binary_packaged ($BINDIR/zcfan present and executable)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: zcfan_binary_packaged ($BINDIR/zcfan missing or not executable)"
    ls -la "$BINDIR" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi
echo "[test] bindir listing:"
ls -la "$BINDIR" 2>&1 || true

# ---------------------------------------------------------------- case 2
# Any argument makes main() print the usage banner and return 0 *before* any
# hardware access.  This is the strongest portable proof that the packaged
# aarch64-linux-ohos binary loads and executes on OHOS: a binary with a broken
# dynamic-link answer would die with rc=127 ("shared library not found"), and
# a musl/ABI mismatch would fault before reaching printf.
echo "[test] case 2: zcfan_usage_banner_exit0"
"$BINDIR/zcfan" show-usage </dev/null >"$TMPDIR/c2.out" 2>"$TMPDIR/c2.err"
RC=$?
if [ "$RC" -eq 0 ] \
   && grep -q "Zero-configuration ThinkPad fan daemon" "$TMPDIR/c2.out" 2>/dev/null \
   && grep -q "See the zcfan(1) man page for details" "$TMPDIR/c2.out" 2>/dev/null; then
    echo "ok: zcfan_usage_banner_exit0 (rc=0, usage banner on stdout)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: zcfan_usage_banner_exit0 (rc=$RC, expected rc=0 + usage banner on stdout)"
    echo "[test] stdout:"; cat "$TMPDIR/c2.out" 2>/dev/null || true
    echo "[test] stderr:"; cat "$TMPDIR/c2.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# The argc!=1 branch ignores the argument *value*: a different argument yields
# byte-identical output.  Also exercises a second exec of the same PIE image
# (relocation/PIE self-consistency on OHOS musl).
echo "[test] case 3: zcfan_usage_arg_independent"
"$BINDIR/zcfan" "--version" </dev/null >"$TMPDIR/c3.out" 2>"$TMPDIR/c3.err"
RC=$?
if [ "$RC" -eq 0 ] && cmp -s "$TMPDIR/c2.out" "$TMPDIR/c3.out"; then
    echo "ok: zcfan_usage_arg_independent (rc=0, output identical for 'show-usage' vs '--version')"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: zcfan_usage_arg_independent (rc=$RC, expected rc=0 and identical banner)"
    diff "$TMPDIR/c2.out" "$TMPDIR/c3.out" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 4
# Runtime hardware contract.  zcfan drives the ThinkPad ACPI fan interface
# /proc/acpi/ibm/fan and upstream deliberately aborts (expect()/abort) when the
# interface is absent — identical behaviour on a non-ThinkPad Linux host.
#   * interface absent  -> immediate FATAL abort, rc=134, site named in stderr
#   * interface present -> the daemon enters its supervision loop and must
#     still be alive when the watchdog timeout fires (timeout(1) -> rc=124)
# Both branches are asserted, so the case is meaningful on either host.
echo "[test] case 4: zcfan_fan_device_contract"
if [ -r /proc/acpi/ibm/fan ]; then
    timeout 5 "$BINDIR/zcfan" </dev/null >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
    RC=$?
    if [ "$RC" -eq 124 ]; then
        echo "ok: zcfan_fan_device_contract (thinkpad_acpi present, daemon alive after 5s, rc=124)"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo "FAIL: zcfan_fan_device_contract (rc=$RC, expected rc=124 long-running daemon)"
        cat "$TMPDIR/c4.err" 2>/dev/null || true
        FAIL_COUNT=$((FAIL_COUNT+1))
    fi
else
    "$BINDIR/zcfan" </dev/null >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
    RC=$?
    if [ "$RC" -eq 134 ] && grep -q "full_speed_supported" "$TMPDIR/c4.err" 2>/dev/null; then
        echo "ok: zcfan_fan_device_contract (no thinkpad_acpi: documented abort rc=134 at full_speed_supported)"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo "FAIL: zcfan_fan_device_contract (rc=$RC, expected rc=134 + 'full_speed_supported')"
        echo "[test] stderr:"; cat "$TMPDIR/c4.err" 2>/dev/null || true
        FAIL_COUNT=$((FAIL_COUNT+1))
    fi
fi

# ---------------------------------------------------------------- case 5
# Packaging completeness: the man page and upstream license travel with the
# binary (the recipe copies them instead of running upstream `make install`,
# which bakes the build-time bindir into the generated systemd unit).
echo "[test] case 5: zcfan_manpage_license_packaged"
if [ -f "$PREFIX/share/man/man1/zcfan.1" ] && [ -f "$PREFIX/licenses/LICENSE" ]; then
    echo "ok: zcfan_manpage_license_packaged (zcfan.1 + LICENSE packaged)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: zcfan_manpage_license_packaged (missing $PREFIX/share/man/man1/zcfan.1 or $PREFIX/licenses/LICENSE)"
    ls -la "$PREFIX" "$PREFIX/share/man/man1" "$PREFIX/licenses" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream runtime test suite","reason":"zcfan 1.4.0 ships no test/tests directory and no check/test/TESTS target in its Makefile; upstream CI runs only static analysis (make lint, make clean clang-tidy, make clean clang-everything).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of $TOTAL)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":5,"passedCount":5}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":5,"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi
