#!/bin/sh
# test_package/test_smoke.sh — static smoke test for alpine-chroot-install.
#
# The packaged artifact is a single POSIX shell script. This test verifies
# packaging integrity WITHOUT executing the script: on OHOS `id -u` reports
# "bad uid", which defeats the script's root check and would start a real
# chroot install with network side effects.
#
# Assertions:
#   1. installed script exists in the package bin/ dir
#   2. installed script is executable
#   3. `sh -n` syntax check passes
#   4. script looks like a POSIX shell script (shebang, no binary payload)
#   5. LICENSE file is packaged under licenses/
#
# pipefail note: OHOS /system/bin/sh supports `set -o pipefail` (verified).
# It ensures a mid-pipeline failure (e.g. head/tr/wc) is not silently
# masked by the exit status of the last command in the pipeline.
set -euo pipefail

PKG_ROOT="${1:-}"
TEST_SHELL="${2:-}"

if [ -z "$PKG_ROOT" ] || [ -z "$TEST_SHELL" ]; then
    echo "ERROR: package root and shell path are required" >&2
    exit 1
fi

SCRIPT="$PKG_ROOT/bin/alpine-chroot-install"
LICENSE="$PKG_ROOT/licenses/LICENSE"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# Assertion 1+2: script exists and is executable
[ -f "$SCRIPT" ] || fail "installed script not found: $SCRIPT"
[ -x "$SCRIPT" ] || fail "installed script not executable: $SCRIPT"
echo "PASS: script present and executable: $SCRIPT"

# Assertion 3: syntax check
"$TEST_SHELL" -n "$SCRIPT" || fail "sh -n syntax check failed: $SCRIPT"
echo "PASS: syntax check passed (sh -n)"

# Assertion 4: shell script shape (shebang, no NUL bytes in first 64 bytes).
# NOTE: do NOT use `grep -q "$(printf '\0')"` — grep treats a NUL in the
# pattern as the end of the C string, making the pattern empty so it always
# matches. Count NUL bytes via tr instead.
head -c 64 "$SCRIPT" | LC_ALL=C tr -d '\000' | wc -c | grep -qx '64' \
    || fail "binary payload detected in header: $SCRIPT"
head -c 64 "$SCRIPT" | LC_ALL=C grep -q '^#!' \
    || fail "not a shell script (bad shebang): $SCRIPT"
echo "PASS: shell script shape verified (shebang, no binary payload)"

# Assertion 5: LICENSE packaged
[ -f "$LICENSE" ] || fail "license file not packaged: $LICENSE"
echo "PASS: license file present: $LICENSE"

echo "PASS: alpine-chroot-install smoke test: all 5 assertions passed"
