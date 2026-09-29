#!/bin/sh
# Consumer verification for mklibs: run the installed CLI tools and assert on
# observable output and exit codes.  Invoked from test_package/conanfile.py
# with the conanrun environment (bindirs on PATH).
set -e

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# 1) installed C++ reader reports the upstream version
v=$(mklibs-readelf --version)
case "$v" in
    *0.1.46*) echo "PASS: mklibs-readelf --version -> 0.1.46" ;;
    *) fail "unexpected --version output: $v" ;;
esac

# 2) --help lists every documented option
h=$(mklibs-readelf --help)
for opt in --print-interp --print-needed --print-rpath --print-soname \
           --print-symbols-provided --print-symbols-undefined; do
    case "$h" in
        *"$opt"*) ;;
        *) fail "option missing from --help: $opt" ;;
    esac
done
echo "PASS: mklibs-readelf --help lists all documented options"

# 3) ELF parsing against a real dynamic executable (the reader itself)
self_bin=$(command -v mklibs-readelf) || fail "mklibs-readelf not on PATH"

interp=$(mklibs-readelf -i "$self_bin")
case "$interp" in
    *ld-*) echo "PASS: -i -> $interp" ;;
    *) fail "-i returned unexpected interpreter: '$interp'" ;;
esac

needed=$(mklibs-readelf -n "$self_bin")
case "$needed" in
    *libc*) echo "PASS: -n reports libc" ;;
    *) fail "-n returned unexpected NEEDED list: '$needed'" ;;
esac

rpath=$(mklibs-readelf -R "$self_bin")
echo "PASS: -R executed (rpath='${rpath}')"

# 4) symbol extraction on a real object
mklibs-readelf -p "$self_bin" > /dev/null || fail "-p failed"
mklibs-readelf -u "$self_bin" > /dev/null || fail "-u failed"
echo "PASS: -p/-u symbol extraction"

# 5) Python entry points (bundled Python package must be importable)
bindir=$(dirname "$self_bin")
if command -v python3 > /dev/null 2>&1; then
    python3 "$bindir/mklibs" --version > /dev/null || fail "mklibs --version failed"
    python3 "$bindir/mklibs-copy" --help > /dev/null || fail "mklibs-copy --help failed"
    echo "PASS: python entry points (mklibs / mklibs-copy)"
else
    echo "SKIP: python3 not on PATH, Python entry points not exercised"
fi

echo "test_package: all assertions passed"
