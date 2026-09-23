#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for the installed CWEBx tools.
# $1 is the C compiler taken from the Conan profile (R33: no bare $CC).
#
# All generated files go into a private work directory: the archive tree must
# never collect test by-products (hello.c/.tex, logs, the compiled binary).
set -eu

CC="${1:-clang}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cwebx-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); echo "[ok]   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[fail] $1"; exit 1; }

check_contains() {
    # $1 file, $2 description, $3.. pattern
    f="$1"; desc="$2"; shift 2
    if [ -s "$f" ] && grep -q "$@" "$f"; then ok "$desc"; else bad "$desc"; fi
}

cat > hello.w <<'WEOF'
@* Hello test.
This file exercises CWEBx for the conan test_package.

@d GREETING "hello-from-cwebx"

@ This program is produced by ctanglex from |hello.w|.

@c
#include <stdio.h>

int main(void) {
    printf("%s\n", GREETING);
    return 0;
}
WEOF

echo "[test] banner lines"
ctanglex --version 2>&1 | head -1 | grep -q "This is CTANGLE (version x3.52)" \
    && ok "ctanglex banner is x3.52" || bad "ctanglex banner"
cweavex --version 2>&1 | head -1 | grep -q "This is CWEAVE (Version x3.52)" \
    && ok "cweavex banner is x3.52" || bad "cweavex banner"

echo "[test] ctanglex extracts C from a .w file"
ctanglex hello > ctangle.log 2>&1 || bad "ctanglex exited non-zero"
check_contains hello.c "ctanglex produced hello.c" '#include <stdio.h>'
check_contains hello.c "@d macro reached the C output" '#define GREETING "hello-from-cwebx"'
check_contains hello.c "ctanglex records source line mapping" '^#line '
check_contains hello.c "default run emits CWEBx section markers" '/\*:[0-9]'

echo "[test] the -l option suppresses that line output"
rm -f hello.c
ctanglex -l hello > ctangle_l.log 2>&1 || bad "ctanglex -l exited non-zero"
if [ -s hello.c ] && ! grep -q '/\*:[0-9]' hello.c; then
    ok "-l emits no section markers but keeps the code"
else
    bad "-l output still carries section markers"
fi

echo "[test] cweavex typesets the same file"
cweavex hello > cweave.log 2>&1 || bad "cweavex exited non-zero"
check_contains hello.tex "cweavex produced hello.tex" 'hello-from-cwebx'

echo "[test] the extracted C compiles and runs"
rm -f hello.c
ctanglex hello > ctangle.log 2>&1 || bad "ctanglex re-run failed"
"$CC" -o hello_from_w hello.c > compile.log 2>&1 || { cat compile.log; bad "compile of hello.c failed"; }
if [ -x ./hello_from_w ]; then ok "compiled program is executable"; else bad "compiled program missing"; fi
out=$(./hello_from_w)
if [ "$out" = "hello-from-cwebx" ]; then
    ok "program built from hello.c printed the expected text"
else
    bad "unexpected program output: $out"
fi

echo "[result] assertions passed: $PASS, failed: $FAIL"
