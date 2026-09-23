#!/bin/sh
# 刻意不使用 `set -e`：三条用例需要逐项捕获退出码并全部执行（未知选项用例
# 预期返回非 0）；HMOS 的 toybox sh 亦不支持部分 bash 风格 set 选项。
# 每条命令的 rc 都显式比较，任一不符即 FAIL 退出（fail-fast 语义由脚本自己保证）。
# run_marco_cli.sh - CLI smoke test for the packaged bin/marco (marco 1.26.2)
# on a headless HarmonyOS worker (no X server, no Xvfb).
#
# --version prints PACKAGE_STRING ("marco 1.26.2") and exits 0 *before* any X
# connection (src/core/main.c: meta_parse_options() -> if (print_version)
# exit(EXIT_SUCCESS)); GOptionContext handles --help and rejects unknown
# options before gtk_init() runs, so all three checks need no DISPLAY.
#
# POSIX sh only (no bashisms); the conanfile runs it with the injected
# $SHELL.  No `set -e`/`set -u`/pipefail so each check captures its own rc.
#   $1 = absolute path to the packaged bin/marco
#   $2 = optional package lib dir added to LD_LIBRARY_PATH (conanrun already
#        provides the transitive dependency libdirs)

MARCO_BIN="$1"
PKG_LIBDIR="${2:-}"

if [ -z "$MARCO_BIN" ]; then
    echo "FAIL: marco binary path not provided"
    exit 1
fi
if [ ! -x "$MARCO_BIN" ]; then
    echo "FAIL: $MARCO_BIN not found or not executable"
    exit 1
fi

if [ -n "$PKG_LIBDIR" ] && [ -d "$PKG_LIBDIR" ]; then
    LD_LIBRARY_PATH="${PKG_LIBDIR}:${LD_LIBRARY_PATH:-}"
    export LD_LIBRARY_PATH
fi

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}"
echo "[env] DISPLAY=${DISPLAY:-<unset>}"

discovered=3
passed=0

# 1/3: --version must report PACKAGE_STRING and exit 0 without an X server.
echo "[test 1/$discovered] marco --version"
version_output=$("$MARCO_BIN" --version 2>&1)
rc=$?
echo "$version_output"
if [ $rc -ne 0 ]; then
    echo "FAIL: marco --version exit=$rc"
elif echo "$version_output" | grep -q "marco 1.26.2"; then
    echo "PASS: marco --version reports 'marco 1.26.2' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: unexpected marco --version output"
fi

# 2/3: --help must exit 0 (GOptionContext prints usage before gtk_init).
echo "[test 2/$discovered] marco --help"
"$MARCO_BIN" --help >/dev/null 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    echo "PASS: marco --help exit 0"
    passed=$((passed + 1))
else
    echo "FAIL: marco --help exit=$rc"
fi

# 3/3: an unknown option must be rejected with a non-zero exit code.
echo "[test 3/$discovered] marco --no-such-option"
"$MARCO_BIN" --no-such-option >/dev/null 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    echo "PASS: marco --no-such-option exit=$rc (non-zero)"
    passed=$((passed + 1))
else
    echo "FAIL: marco --no-such-option unexpectedly exited 0"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"run_marco_cli.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"run_marco_cli.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
