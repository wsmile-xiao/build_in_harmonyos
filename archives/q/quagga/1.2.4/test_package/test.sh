#!/data/service/hnp/bin/bash
# test_package/test.sh — quagga 1.2.4 smoke test (runs in the conanrun env)
#
# Every check below is a hard failure: the script exits non-zero if a packaged
# command is missing, if `vtysh` sneaks back in, or if a binary does not execute
# and report its version.  Nothing here degrades a miss into a printed notice.
set -eu

# The packaged command set — must stay identical to the "commands" list of
# archives/q/quagga/commands.json and to test_package/conanfile.py::_BINARIES.
COMMANDS="zebra bgpd ripd ripngd ospfd ospf6d isisd pimd watchquagga"

echo "[test] every packaged command is installed and reachable on PATH"
missing=""
for bin in $COMMANDS; do
    command -v "$bin" >/dev/null 2>&1 || missing="$missing $bin"
done
if [ -n "$missing" ]; then
    echo "FAIL: not installed/on PATH:$missing"
    exit 1
fi

echo "[test] --disable-vtysh/--disable-nhrpd took effect: neither may be installed"
for gone in vtysh nhrpd; do
    if command -v "$gone" >/dev/null 2>&1; then
        echo "FAIL: $gone is installed although the recipe disables it"
        exit 1
    fi
done

echo "[test] each binary executes and reports the packaged version"
for bin in $COMMANDS; do
    # `set -e` makes a non-zero exit here a hard failure, which is the point:
    # it proves the ELF loads and its relocations resolve on OHOS.
    out=$("$bin" --version 2>&1)
    case "$out" in
        *1.2.4*) echo "  ok  $bin -> $out" ;;
        *)       echo "FAIL: $bin --version carries no version: $out"; exit 1 ;;
    esac
done

echo "✅ quagga test.sh finished"
