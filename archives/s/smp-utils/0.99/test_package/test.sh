#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the smp-utils binaries on OHOS
#
# Exercises the installed package (R34):
#   1. Discovers every installed bin/smp_* binary (no hardcoded list) and
#      runs --version on each (upstream prints "version: <str>").
#   2. --help on two representative tools (usage text).
#   3. Graceful missing-device failure: exit 92 (SMP_LIB_FILE_ERROR, not a
#      segfault) with the device name in stderr — holds on OHOS where no
#      SAS device exists.
#
# Returns 0 on success, non-zero on any failure. Each check is an
# assertion counted in MANIFEST.yml.
set -u

PASS=0
FAIL=0

assert_pass() {
    PASS=$((PASS + 1))
    echo "ok  $1"
}

assert_fail() {
    FAIL=$((FAIL + 1))
    echo "FAIL $1${2:+ — $2}"
}

# OHOS /tmp is read-only; use a writable scratch under the test_package dir.
SCRATCH="$(cd "$(dirname "$0")" && pwd)/.scratch"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

# Locate the installed binaries via PATH (conanfile prepends pkg bin/).
if ! command -v smp_rep_general >/dev/null 2>&1; then
    echo "FAIL smp-utils binaries not found on PATH"
    exit 1
fi
SMP_BIN_DIR="$(dirname "$(command -v smp_rep_general)")"
echo "[test] using binaries from: $SMP_BIN_DIR"

# --- 1. --version on every installed smp_* binary (no hardcoded list) ------
BIN_COUNT=0
for b in "$SMP_BIN_DIR"/smp_*; do
    [ -f "$b" ] || continue
    BIN_COUNT=$((BIN_COUNT + 1))
    name="$(basename "$b")"
    out="$("$b" --version 2>&1)"
    if echo "$out" | grep -q "version:"; then
        assert_pass "$name --version"
    else
        assert_fail "$name --version" "$out"
    fi
done
if [ "$BIN_COUNT" -lt 29 ]; then
    assert_fail "installed smp_* binary count >= 29" "found $BIN_COUNT"
else
    assert_pass "installed smp_* binary count >= 29 (found $BIN_COUNT)"
fi

# --- 2. --help on two representatives --------------------------------------
for tool in smp_rep_general smp_discover_list; do
    out="$("$SMP_BIN_DIR/$tool" --help 2>&1)"
    if echo "$out" | grep -qi "usage"; then
        assert_pass "$tool --help mentions usage"
    else
        assert_fail "$tool --help mentions usage" "$(echo "$out" | head -2)"
    fi
done

# --- 3. graceful missing-device failure -------------------------------------
for tool in smp_rep_general smp_discover; do
    # stdout is irrelevant here: the checks look at the exit code and at
    # stderr, which is captured into $SCRATCH/err.txt.
    "$SMP_BIN_DIR/$tool" /dev/no-such-smp-dev 2>"$SCRATCH/err.txt"
    rc=$?
    if [ "$rc" -eq 92 ]; then
        assert_pass "$tool missing-device exit == 92 (SMP_LIB_FILE_ERROR)"
    else
        assert_fail "$tool missing-device exit == 92" "got $rc"
    fi
    if grep -q "no-such-smp-dev" "$SCRATCH/err.txt"; then
        assert_pass "$tool missing-device stderr mentions device"
    else
        assert_fail "$tool missing-device stderr mentions device" \
            "$(head -2 "$SCRATCH/err.txt")"
    fi
done

# --- 4. static linking sanity (R26) ----------------------------------------
if command -v readelf >/dev/null 2>&1; then
    BIN="$SMP_BIN_DIR/smp_rep_general"
    if readelf -h "$BIN" >"$SCRATCH/elfh.txt" 2>&1; then
        elf_type=$(grep "Type:" "$SCRATCH/elfh.txt" | head -1 | awk '{print $2}')
        if [ "$elf_type" = "EXEC" ] || [ "$elf_type" = "DYN" ]; then
            assert_pass "smp_rep_general has valid ELF type ($elf_type)"
        else
            assert_fail "smp_rep_general ELF type unexpected" "$elf_type"
        fi
    else
        assert_fail "readelf -h failed on smp_rep_general"
    fi
    needed=$(readelf -d "$BIN" 2>/dev/null | grep NEEDED || true)
    if [ -z "$needed" ]; then
        assert_pass "smp_rep_general has no NEEDED libs (fully static)"
    else
        assert_fail "smp_rep_general has dynamic deps" "$needed"
    fi
else
    echo "[skip] readelf not available; skipping ELF/static checks"
fi

echo "[summary] pass=$PASS fail=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
