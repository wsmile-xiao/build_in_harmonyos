#!/bin/sh
# test_ksh.sh — functional smoke test executed BY the packaged ksh binary.
# Asserts real shell behaviour; prints "ok:" / "FAIL:" lines (L1b evidence).
#
# NOTE: set -e is intentionally NOT used: check() captures each command's exit
# status per assertion, and set -e would abort the script on the first failure
# instead of reporting all assertions (code-style §7, documented deviation).
set -u
set -o pipefail

fail=0

check() {
    desc=$1
    shift
    if "$@"; then
        echo "  ok: $desc"
    else
        echo "  FAIL: $desc"
        fail=1
    fi
}

check "arithmetic expansion"        test "$(echo $((3 * 7)))" = "21"
check "parameter substitution"      test "$(s=hello; echo ${s%lo})" = "hel"
check "for loop"                    test "$(for i in a b c; do printf '%s' "$i"; done)" = "abc"
check "while loop"                  test "$(x=5; while [ "$x" -gt 0 ]; do x=$((x-1)); done; echo "$x")" = "0"
check "conditional test"            test "$(if [ 1 -lt 2 ]; then echo yes; fi)" = "yes"
check "command substitution"        test "$(echo $(echo nested))" = "nested"
check "pipe"                        test "$(printf 'a\nb\nc\n' | wc -l)" = "3"
check "KSH_VERSION is set"          test -n "$KSH_VERSION"
check "positional parameters"       test "$(set -- x y z; echo "$#:$2")" = "3:y"

if [ "$fail" = 1 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS — all ksh93u-m smoke tests passed"
