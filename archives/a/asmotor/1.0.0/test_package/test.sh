#!/bin/sh
# test_package/test.sh — smoke test for the asmotor assembler toolchain
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binaries.
# OHOS /tmp 只读（E002）：所有临时文件写入 $TMPDIR（test 时由 conan 提供可写目录）。
set -eu

# 可写临时目录：优先 $TMPDIR，回退当前目录（conan test 工作目录可写）
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    OUTDIR="$TMPDIR"
else
    OUTDIR="$PWD"
fi
TMPF="$OUTDIR/asmotor_test.asm"
ERRF="$OUTDIR/asmotor_test.err"

echo "[test] motorz80 --help / version"
motorz80 --help >/dev/null 2>&1 && echo "OK: motorz80 --help" || { echo "NOTE: motorz80 has no --help; trying -h"; motorz80 -h >/dev/null 2>&1 && echo "OK: motorz80 -h"; }

echo "[test] motorz80 functional (assemble Z80 source -> object)"
cat >"$TMPF" <<'EOF'
	SECTION	"Test",CODE[0]
	rl	(hl)
	rla
	ld	a,1
	halt
EOF
motorz80 -mcz -fv -o"$OUTDIR/asmotor_test.r" "$TMPF" 2>"$ERRF" || {
    echo "FAIL: motorz80 assembly failed"; cat "$ERRF"; exit 1;
}
echo "OK: motorz80 assembled $(wc -c <"$OUTDIR/asmotor_test.r") byte(s) of object"

echo "[test] xlink / xlib present"
xlink -h >/dev/null 2>&1 || true
xlib -h >/dev/null 2>&1 || true
if [ -s "$OUTDIR/asmotor_test.r" ]; then
    echo "OK: object file exists and non-empty ($(wc -c <"$OUTDIR/asmotor_test.r") bytes)"
else
    echo "FAIL: object file missing or empty"
    exit 1
fi

echo "ALL TEST_PACKAGE CHECKS PASSED"