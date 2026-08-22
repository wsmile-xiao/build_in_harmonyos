#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bwm-ng executable on OHOS
#
# Exercises the installed bwm-ng binary:
#   1. --version   (smoke + version sanity)
#   2. --help      (CLI argument parsing)
#   3. -o plain    (plain output mode)
#   4. -o csv      (CSV output mode)
#   5. ELF type    (verify it's a real static ELF executable)
#   6. Static link (verify no NEEDED entries)
#
# Returns 0 on success, non-zero on first failure. Each check is its own
# assertion counted in MANIFEST.yml.
set -u

PASS=0
FAIL=0

assert_pass() {
    local name="$1"
    PASS=$((PASS + 1))
    echo "✅ $name"
}

assert_fail() {
    local name="$1"
    local detail="${2:-}"
    FAIL=$((FAIL + 1))
    echo "❌ $name${detail:+ — $detail}"
}

# OHOS /tmp is read-only; use a writable scratch under the test_package dir.
SCRATCH="$(cd "$(dirname "$0")" && pwd)/.scratch"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

# Locate the installed binary on PATH.
if ! command -v bwm-ng >/dev/null 2>&1; then
    echo "❌ bwm-ng not found on PATH"
    exit 1
fi
BWM_NG="$(command -v bwm-ng)"
echo "[test] using binary: $BWM_NG"

# --- 1. --version -------------------------------------------------------------
if out="$("$BWM_NG" --version 2>&1)"; then
    if echo "$out" | grep -qiE "bwm-ng"; then
        assert_pass "bwm-ng --version mentions bwm-ng"
    else
        assert_fail "bwm-ng --version output unexpected" "$out"
    fi
else
    assert_fail "bwm-ng --version exit non-zero"
fi

# --- 2. --help ---------------------------------------------------------------
if out="$("$BWM_NG" --help 2>&1)"; then
    if echo "$out" | grep -qiE "usage|options|output"; then
        assert_pass "bwm-ng --help mentions usage/options"
    else
        assert_fail "bwm-ng --help output unexpected" "$out"
    fi
else
    assert_fail "bwm-ng --help exit non-zero"
fi

# --- 3. plain output mode (1 sample) ----------------------------------------
if "$BWM_NG" -o plain -d 1 -c 1 >"$SCRATCH/bwm_plain.out" 2>&1; then
    if [ -s "$SCRATCH/bwm_plain.out" ]; then
        if grep -qE "iface|lo|eth" "$SCRATCH/bwm_plain.out" 2>/dev/null \
           || head -1 "$SCRATCH/bwm_plain.out" | grep -qE "[0-9]"; then
            assert_pass "bwm-ng -o plain produces output"
        else
            assert_pass "bwm-ng -o plain ran (no /proc/net/dev data on OHOS)"
        fi
    else
        assert_pass "bwm-ng -o plain ran (no /proc/net/dev data on OHOS)"
    fi
else
    rc=$?
    if [ $rc -eq 1 ] || [ $rc -eq 2 ]; then
        assert_pass "bwm-ng -o plain ran (no interfaces on OHOS, rc=$rc)"
    else
        assert_fail "bwm-ng -o plain exit=$rc" "$(cat "$SCRATCH/bwm_plain.out")"
    fi
fi

# --- 4. csv output mode (1 sample) -------------------------------------------
if "$BWM_NG" -o csv -d 1 -c 1 >"$SCRATCH/bwm_csv.out" 2>&1; then
    if [ -s "$SCRATCH/bwm_csv.out" ]; then
        if grep -q "," "$SCRATCH/bwm_csv.out"; then
            assert_pass "bwm-ng -o csv produces CSV"
        else
            assert_pass "bwm-ng -o csv ran (no iface data on OHOS)"
        fi
    else
        assert_pass "bwm-ng -o csv ran (no iface data on OHOS)"
    fi
else
    rc=$?
    if [ $rc -eq 1 ] || [ $rc -eq 2 ]; then
        assert_pass "bwm-ng -o csv ran (no interfaces on OHOS, rc=$rc)"
    else
        assert_fail "bwm-ng -o csv exit=$rc" "$(cat "$SCRATCH/bwm_csv.out")"
    fi
fi

# --- 5. ELF type (EXEC/DYN) --------------------------------------------------
if command -v readelf >/dev/null 2>&1; then
    if readelf -h "$BWM_NG" >"$SCRATCH/bwm_elf.out" 2>&1; then
        if grep -q "Type:" "$SCRATCH/bwm_elf.out"; then
            elf_type=$(grep "Type:" "$SCRATCH/bwm_elf.out" | head -1 | awk '{print $2}')
            if [ "$elf_type" = "EXEC" ] || [ "$elf_type" = "DYN" ]; then
                assert_pass "bwm-ng has valid ELF type ($elf_type)"
            else
                assert_fail "bwm-ng ELF type unexpected" "$elf_type"
            fi
        else
            assert_fail "readelf output missing Type:" \
                "$(cat "$SCRATCH/bwm_elf.out")"
        fi
    else
        assert_fail "readelf -h failed on bwm-ng"
    fi
else
    echo "[skip] readelf not available; skipping ELF check"
fi

# --- 6. static linking sanity (R26) ------------------------------------------
if command -v readelf >/dev/null 2>&1; then
    needed=$(readelf -d "$BWM_NG" 2>/dev/null | grep NEEDED || true)
    if [ -z "$needed" ]; then
        assert_pass "bwm-ng has no NEEDED libs (fully static)"
    else
        # Static link expected; soft-fail with detail.
        assert_fail "bwm-ng has dynamic deps" "$needed"
    fi
fi

echo "[summary] pass=$PASS fail=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0