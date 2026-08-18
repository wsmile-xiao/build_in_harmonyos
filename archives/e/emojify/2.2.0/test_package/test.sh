#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for emojify
# Runs in conanrun env (VirtualRunEnv puts installed bin/ on PATH).
# Test cases are derived from the upstream emojify_tests.bats.
set -euo pipefail

pass=0
fail=0

check() {
    # check <input> <expected>
    local input="$1"
    local expected="$2"
    local actual
    actual="$(emojify "$input")"
    if [[ "$actual" == "$expected" ]]; then
        echo "[ok] emojify \"$input\" => \"$actual\""
        pass=$((pass + 1))
    else
        echo "[FAIL] emojify \"$input\""
        echo "   expected: \"$expected\""
        echo "   actual:   \"$actual\""
        fail=$((fail + 1))
    fi
}

echo "[test] emojify functional tests (from upstream emojify_tests.bats)"

# Case 1: single emoji substitution
check "an emoji :grin:" "an emoji 😁"

# Case 2: no emoji in input (unchanged)
check "no emoji :(" "no emoji :("

# Case 3: multiple / adjacent emojis
check "emojis :grin::grin: :tada:yay:champagne:" "emojis 😁😁 🎉yay🍾"

# Case 4: emoji with underscore and number
check "this is perfect :100: :1st_place_medal:" "this is perfect 💯 🥇"

# Case 5: +1 / -1 aliases
check "great :+1::+1::-1:" "great 👍👍👎"

# --- version option ---
if emojify --version | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "[ok] emojify --version returns a version string"
    pass=$((pass + 1))
else
    echo "[FAIL] emojify --version did not return a version"
    fail=$((fail + 1))
fi

echo ""
echo "[result] passed=$pass failed=$fail"

if [[ $fail -gt 0 ]]; then
    exit 1
fi
exit 0
