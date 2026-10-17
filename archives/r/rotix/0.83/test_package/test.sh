#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the installed rotix binary.
#
# Runs in the conanrun environment (PATH includes the installed bin/).
# rotix rotates only ASCII letters A-Z / a-z; every other byte passes through.
# All expected values below are derived from upstream rot.c rotate():
#   rotor %= 26; rotor < 0 -> += 26; uppercase A-Z and lowercase a-z shifted.
set -u

# /system/bin (mksh) cannot execute ELF binaries; ensure coreutils are reachable.
export PATH="$PATH:/system/bin"

fail=0
check() { # check <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 (expected [$2], got [$3])"
        fail=$((fail + 1))
    fi
}

echo "--- rotix consumer verification ---"

# 1. Default rotor is 13 and rotates right.
check "default ROT13" "Uryyb, Jbeyq!" "$(rotix -t 'Hello, World!')"
# 2. ROT13 is its own inverse.
check "ROT13 roundtrip" "Hello" "$(rotix -t 'Uryyb')"
# 3. rotor 0 is the identity.
check "rotor 0 identity" "abc" "$(rotix -t 'abc' -r 0)"
# 4. rotor 26 wraps to the identity.
check "rotor 26 identity" "abc" "$(rotix -t 'abc' -r 26)"
# 5. -L rotates left.
check "left rotate 3" "xyz" "$(rotix -t 'abc' -r 3 -L)"
# 6. Upper and lower case are rotated independently.
check "case preserved" "NoP" "$(rotix -t 'AbC' -r 13)"
# 7. --version reports the tool name.
if rotix -v | grep -q "Rotix version"; then
    echo "PASS: --version"
else
    echo "FAIL: --version did not report the version"
    fail=$((fail + 1))
fi
# 8. -h prints usage and exits 0.
if rotix -h >/dev/null 2>&1; then
    echo "PASS: -h exits 0"
else
    echo "FAIL: -h returned non-zero"
    fail=$((fail + 1))
fi
# 9. With no input option, rotix reads stdin.
check "stdin default" "Uryyb" "$(printf 'Hello\n' | rotix)"
# 10. -f - explicitly reads stdin.
check "-f - reads stdin" "Uryyb" "$(printf 'Hello\n' | rotix -f -)"
# 11. Combining a text and an input file is rejected.
if rotix -t x -f - >/dev/null 2>&1; then
    echo "FAIL: conflicting -t/-f was accepted"
    fail=$((fail + 1))
else
    echo "PASS: conflicting -t/-f rejected"
fi
# 12. -a on a text emits all 25 ROT-x lines; the ROT-13 line must be present.
out="$(rotix -a -t Hello)"
if printf '%s\n' "$out" | grep -q "^ROT-13: Uryyb$"; then
    echo "PASS: -a emits ROT-13 line"
else
    echo "FAIL: -a ROT-13 line missing"
    fail=$((fail + 1))
fi
# 13. -a emits exactly 25 lines.
check "-a line count" "25" "$(printf '%s\n' "$out" | wc -l | tr -d ' ')"

if [ "$fail" -ne 0 ]; then
    echo "rotix test_package: $fail assertion(s) FAILED"
    exit 1
fi
echo "rotix test_package: 13/13 assertions PASS"
exit 0
