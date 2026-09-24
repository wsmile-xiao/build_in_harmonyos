#!/bin/sh
# Real CLI checks for the installed tradcpp.
#
# Run by test_package/conanfile.py as `sh test.sh <workdir>`; the installed
# binary is on PATH through Conan's run environment.  Every failing check
# exits non-zero, which makes conan's test() fail.
#
# POSIX sh only, and deliberately built from shell builtins (`case`, `[`,
# `read`) — no diff/cmp/wc, so it does not depend on which utilities the
# worker image happens to ship.
set -eu

workdir="${1:-.}"
cd "$workdir"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# The input relies on semantics only a *traditional* preprocessor has:
#   concat(abc,def) with `#define concat(a, b) a/**/b` -> abcdef  (K&R token paste)
#   STR(hello)      with `#define STR(x) #x`          -> #hello (no ISO
#                                                      stringification)
cat > input.c <<'EOF'
#define concat(a, b) a/**/b
#define STR(x) #x
concat(abc,def)
STR(hello)
#ifdef GREETING
GREETING
#endif
EOF

tradcpp -DGREETING=bonjour input.c output.txt

# Compare line by line against the expected output.
expected_1="abcdef"
expected_2="#hello"
expected_3="bonjour"

n=0
while IFS= read -r line; do
    n=$((n + 1))
    case $n in
        1) [ "$line" = "$expected_1" ] || fail "line 1 is '$line', expected '$expected_1'" ;;
        2) [ "$line" = "$expected_2" ] || fail "line 2 is '$line', expected '$expected_2' (traditional semantics broken: '#' must not stringify)" ;;
        3) [ "$line" = "$expected_3" ] || fail "line 3 is '$line', expected '$expected_3'" ;;
        *) fail "unexpected extra output line $n: '$line'" ;;
    esac
done < output.txt

[ "$n" -eq 3 ] || fail "expected exactly 3 output lines, got $n"

echo "ok   tradcpp produced the expected 3 lines"
echo "ok   K&R token paste (a/**/b) works"
echo "ok   traditional semantics preserved: '#' is not stringified"
echo "all tradcpp CLI checks passed"
