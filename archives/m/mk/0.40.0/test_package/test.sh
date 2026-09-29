#!/bin/sh
# test.sh — consumer-side end-to-end test for the packaged mk (mk-configure) 0.40.0
#
# Driven by test_package/conanfile.py::test() with MK_PKG pointing at the
# installed package folder.  It builds a real C project with the packaged
# "mkcmake" wrapper (include library from share/mk-configure) and runs the
# produced program, then exercises the packaged mkc_check_version helper.
set -e

MK_PKG="${MK_PKG:?MK_PKG (mk package folder) must be set}"
MKCMAKE="$MK_PKG/bin/mkcmake"
MKC_CHECK_VERSION="$MK_PKG/bin/mkc_check_version"

workdir="${TMPDIR:-/tmp}/mk-conan-test-$$"
rm -rf "$workdir"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' 0

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

echo "== 1/3. build a C project with the packaged mkcmake =="
(cd "$workdir" && "$MKCMAKE" all)

echo "== 2/3. run the produced program =="
output=$("$workdir/hello")
echo "   program output: $output"
if [ "$output" != "hello-from-mkcmake" ]; then
    echo "FAIL: unexpected program output: $output"
    exit 1
fi

echo "== 3/3. use the packaged mkc_check_version helper =="
"$MKC_CHECK_VERSION" 0.10.0 0.40.0 > /dev/null

echo "OK: mk/0.40.0 consumer test passed"
