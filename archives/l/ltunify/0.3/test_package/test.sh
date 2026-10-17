#!/data/service/hnp/bin/bash
# test_package/test.sh - ltunify 0.3 functional assertions.
# Runs in the conanrun environment, so bin/ is on PATH.
#
# ltunify is a hardware tool: every "real" code path opens /dev/hidraw* and
# talks to a Logitech Unifying receiver. No receiver is attached to the build
# hosts and the hidraw nodes are not openable, so the device I/O surface is
# NOT covered here - see notes.md for the explicit uncovered list.
set -uo pipefail

pass=0
fail=0
ok()   { pass=$((pass + 1)); echo "  PASS $*"; }
bad()  { fail=$((fail + 1)); echo "  FAIL $*"; }

echo "[1/4] binaries are exported into the consumer runenv"
if command -v ltunify >/dev/null 2>&1; then ok "ltunify on PATH"; else bad "ltunify not on PATH"; fi
if command -v read-dev-usbmon >/dev/null 2>&1; then ok "read-dev-usbmon on PATH"; else bad "read-dev-usbmon not on PATH"; fi

echo "[2/4] ltunify --version reports the packaged upstream version"
vout=$(ltunify --version 2>&1); vrc=$?
if [ "$vrc" -eq 0 ] && printf '%s' "$vout" | grep -q "version 0.3"; then
    ok "--version -> 0.3"
else
    bad "--version rc=$vrc out=[$vout]"
fi

echo "[3/4] ltunify --help advertises the three pairing subcommands"
hout=$(ltunify --help 2>&1)
for cmd in list pair unpair; do
    if printf '%s' "$hout" | grep -q "$cmd"; then ok "help mentions $cmd"; else bad "help lacks $cmd"; fi
done

echo "[4/4] read-dev-usbmon rejects a missing device argument with usage"
rout=$(read-dev-usbmon </dev/null 2>&1); rrc=$?
if [ "$rrc" -ne 0 ] && printf '%s' "$rout" | grep -q "Usage:"; then
    ok "usage error, rc=$rrc"
else
    bad "rc=$rrc out=[$rout]"
fi

echo "----------------------------------------"
echo "assertions: $((pass + fail))  passed: $pass  failed: $fail"
[ "$fail" -eq 0 ] || exit 1
echo "ALL TESTS PASSED"
