#!/bin/sh
# test.sh — consumer-side end-to-end test for the packaged mkc (mk-configure) 0.27.0
#
# Driven by test_package/conanfile.py::test() with MKC_PKG pointing at the
# installed package folder.  It builds a real C project with the packaged
# "mkcmake" wrapper (include library from share/mkc-mk) and runs the
# produced program, then exercises the packaged mkc_check_* helpers.
set -e

MKC_PKG="${MKC_PKG:?MKC_PKG (mkc package folder) must be set}"
MKCMAKE="$MKC_PKG/bin/mkcmake"
MKC_CHECK_VERSION="$MKC_PKG/bin/mkc_check_version"
MKC_CHECK_HEADER="$MKC_PKG/bin/mkc_check_header"
MKC_CHECK_SIZEOF="$MKC_PKG/bin/mkc_check_sizeof"

workdir="${TMPDIR:-/tmp}/mkc-conan-test-$$"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' 0

# mkc's helpers fall back to bare "cc" which does not exist on HarmonyOS/OHOS;
# make sure the compiler used by mkcmake and the mkc_check_* scripts is the
# clang that is on PATH in this environment.
CC_BIN=$(command -v clang || command -v cc || true)
if [ -n "$CC_BIN" ]; then
    CC="$CC_BIN"
    export CC
fi

cat > "$workdir/hello.c" <<'EOF'
#include <stdio.h>

int main(void)
{
    printf("hello-from-mkcmake\n");
    return 0;
}
EOF

cat > "$workdir/Makefile" <<'EOF'
PROG=	hello
SRCS=	hello.c

.include <mkc.prog.mk>
EOF

echo "== 1/4. build a C project with the packaged mkcmake =="
(cd "$workdir" && "$MKCMAKE" all)

echo "== 2/4. run the produced program =="
output=$("$workdir/hello")
echo "   program output: $output"
if [ "$output" != "hello-from-mkcmake" ]; then
    echo "FAIL: unexpected program output: $output"
    exit 1
fi

echo "== 3/4. use the packaged mkc_check_version helper =="
"$MKC_CHECK_VERSION" 0.10.0 0.27.0 > /dev/null

echo "== 4/4. use the packaged mkc_check_header / mkc_check_sizeof helpers =="
hdr_result=$("$MKC_CHECK_HEADER" stdio.h)
echo "   mkc_check_header stdio.h -> $hdr_result"
if [ "$hdr_result" != "1" ]; then
    echo "FAIL: unexpected mkc_check_header result: $hdr_result"
    exit 1
fi
sz_result=$("$MKC_CHECK_SIZEOF" int)
echo "   mkc_check_sizeof int -> $sz_result"
case "$sz_result" in
    4) ;;
    *) echo "FAIL: unexpected mkc_check_sizeof result: $sz_result"; exit 1 ;;
esac

echo "OK: mkc/0.27.0 consumer test passed"
