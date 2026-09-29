#!/bin/sh
# Consumer contract runner for libgridxc 2.1.02.0.2.
# Runs both Fortran contract binaries and asserts their PASS markers.
# Exists so CI L0c (which only counts .c/.cpp/.cc/.cxx/.sh/.py sources)
# recognises this Fortran package's consumer tests; it is the real
# execution path invoked from test_package/conanfile.py test().
set -eu

BINDIR="${1:-.}"
fail() {
    echo "FAIL: $1"
    exit 1
}

for name in lda_contract gga_contract; do
    bin="$BINDIR/$name"
    [ -f "$bin" ] || fail "$bin not found"
    out=$("$bin" 2>&1) || fail "$name exited non-zero: $out"
    echo "$out"
    case "$out" in
        *"GRIDXC_TEST $name PASS"*) echo "PASS: $name contract" ;;
        *) fail "$name missing PASS marker" ;;
    esac
done

echo "libgridxc test_package: OK"
exit 0
