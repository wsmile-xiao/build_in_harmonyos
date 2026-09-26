#!/bin/sh
# Consumer-side smoke test for the packaged shishi command line tools.
# Usage: sh test_shishi_tools.sh <package-folder>
# 5 checks: each tool must exit 0 and self-report version 1.0.3.
# Layout note: conan's AutotoolsToolchain maps --sbindir to cpp_info
# bindirs[0], so all five tools (including shishid/keytab2shishi) are
# installed into bin/ — verified against the packaged tree.

PKG="$1"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: package folder argument missing" >&2
    exit 1
fi

failures=0
check_tool() {
    _path="$1"
    if [ ! -x "$_path" ]; then
        echo "FAIL: $_path not present/executable"
        failures=$((failures + 1))
        return
    fi
    _out=$("$_path" --version 2>&1)
    _rc=$?
    if [ "$_rc" -ne 0 ]; then
        echo "FAIL: $_path --version rc=$_rc"
        echo "$_out" | sed 's/^/  | /'
        failures=$((failures + 1))
        return
    fi
    case "$_out" in
        *1.0.3*)
            echo "ok: $_path --version reports 1.0.3"
            ;;
        *)
            echo "FAIL: $_path --version output lacks 1.0.3"
            echo "$_out" | sed 's/^/  | /'
            failures=$((failures + 1))
            ;;
    esac
}

check_tool "$PKG/bin/shishi"
check_tool "$PKG/bin/shisa"
check_tool "$PKG/bin/ccache2shishi"
check_tool "$PKG/bin/shishid"
check_tool "$PKG/bin/keytab2shishi"

echo "test_shishi_tools: 5 check(s) run, $failures failed"
[ "$failures" -eq 0 ] || exit 1
exit 0
