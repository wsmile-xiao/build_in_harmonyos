#!/bin/sh
# alcotest test_package smoke test — verify OCaml library artifacts exist
# alcotest is an OCaml library, not a C/C++ library.
# We verify the key compiled artifacts are present and valid.

PKG_LIB="${1:-.}"
FAIL=0
PASS=0

check_file() {
    if [ -f "$PKG_LIB/$1" ]; then
        PASS=$((PASS + 1))
    else
        echo "MISSING: $1"
        FAIL=$((FAIL + 1))
    fi
}

# Main alcotest library
check_file "lib/alcotest/alcotest.cma"
check_file "lib/alcotest/alcotest.cmxa"
check_file "lib/alcotest/alcotest.a"
check_file "lib/alcotest/alcotest.cmi"
check_file "lib/alcotest/libalcotest_stubs.a"
check_file "lib/alcotest/META"

# alcotest.engine sub-library
check_file "lib/alcotest/engine/alcotest_engine.cma"
check_file "lib/alcotest/engine/alcotest_engine.cmxa"
check_file "lib/alcotest/engine/alcotest_engine.a"

# alcotest.stdlib_ext sub-library
check_file "lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cma"
check_file "lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cmxa"
check_file "lib/alcotest/stdlib_ext/alcotest_stdlib_ext.a"

echo "alcotest artifact check: $PASS passed, $FAIL missing"
if [ $FAIL -ne 0 ]; then
    exit 1
fi
exit 0
