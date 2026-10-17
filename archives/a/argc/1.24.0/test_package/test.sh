#!/bin/sh
# test_package/test.sh — smoke test for argc executable
# Runs in conanrun env (PATH includes installed bin/)
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
#
# NOTE: argc's own CLI only recognizes `--argc-*` prefixed flags
# (--argc-help / --argc-version / --argc-eval ...). Plain `--version`
# / `--help` are *script-level* flags and require an Argcfile in the
# current directory, so they are not usable here (no Argcfile present).
#
# HMBS 平台诊断 shell_getcwd：HNP bash 在 HMFS/HMDFS 工作目录启动时
# getcwd 失败，会在 stderr 打印一条无害的 `shell-init:` 警告。harness
# 本身由注入的 /bin/sh 执行（CONFIG_SHELL），不受影响；第 3 个用例
# 需要 bash 运行 argc 脚本，比对前剥离该环境产物行（非脚本输出）。
set -uo pipefail

PASS=0
FAIL=0

# cd to a writable directory (HMBS TMPDIR; OHOS /tmp is read-only)
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"

echo "[test] argc --argc-version"
VERSION_OUT=$(argc --argc-version 2>&1)
if printf '%s' "$VERSION_OUT" | grep -q "argc 1.24.0"; then
    PASS=$((PASS + 1))
    echo "[ok] --argc-version prints 'argc 1.24.0'"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --argc-version output unexpected: $VERSION_OUT"
fi

echo "[test] argc --argc-help"
HELP_OUT=$(argc --argc-help 2>&1)
if printf '%s' "$HELP_OUT" | grep -q "USAGE"; then
    PASS=$((PASS + 1))
    echo "[ok] --argc-help shows USAGE section"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --argc-help output unexpected: $HELP_OUT"
fi

echo "[test] argc parses an argc-annotated script with options"
cat > test_argc_demo.sh <<'EOF'
# @describe Demo script for argc test_package

# @cmd Say hello
# @option --name! Your name
hello() {
    echo "hello,$argc_name"
}

eval "$(argc --argc-eval "$0" "$@")"
EOF
# argc-based scripts are plain bash scripts; run them with bash. The
# script's eval line invokes `argc --argc-eval "$0" "$@"`, which parses
# the annotations and dispatches the `hello` subcommand with --name world.
# HNP bash prints a harmless `shell-init:` getcwd warning at startup when
# launched in an HMFS/HMDFS working directory (HMBS platform diagnostic
# shell_getcwd); strip that artifact line before comparing — it is an
# environment diagnostic, not script output.
BASH_BIN=$(command -v bash 2>/dev/null)
OUT=$("$BASH_BIN" test_argc_demo.sh hello --name world 2>&1)
RC=$?
OUT=$(printf '%s\n' "$OUT" | sed '/^shell-init:/d')
if [ "$RC" -eq 0 ] && [ "$OUT" = "hello,world" ]; then
    PASS=$((PASS + 1))
    echo "[ok] script option parsing produced: $OUT"
else
    FAIL=$((FAIL + 1))
    echo "[fail] script option parsing rc=$RC output: $OUT"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":3,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
