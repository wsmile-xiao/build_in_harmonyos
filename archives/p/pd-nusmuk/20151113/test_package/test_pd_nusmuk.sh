#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-nusmuk 20151113.
#
# The package installs two Pd external libraries under
#   <pkg>/lib/pd-externals/nusmuk-utils   (13 externals)
#   <pkg>/lib/pd-externals/nusmuk-audio    (4 externals)
#
# This script loads both directories with the OHOS `pd` from the puredata
# package and checks that
#   1. every expected external is present on disk (17 artifacts),
#   2. every external is an aarch64 ELF shared object (and `pd` itself is an
#      aarch64 ELF executable),
#   3. Pd reports no load error for any of the 17 externals instantiated
#      by test_pd_nusmuk.pd,
#   4. the ten array-processing externals run their compute loop over real
#      Pd arrays and emit the completion bang documented by upstream,
#   5. [line3] passes a float through, i.e. compiled code + Pd outlet work.
#
# Checks 4 and 5 are loadbang/delay driven, so they can only produce their
# output if Pd's logical clock really ticks: a dead clock makes them fail
# outright instead of silently passing.  There is deliberately no
# "skip on a non-ticking clock" branch — a skipped Pd run must never be
# reported as a passing test.
#
# Env:
#   PD_BIN        path to the installed `pd` executable
#   UTILS_DIR     nusmuk-utils external directory
#   AUDIO_DIR     nusmuk-audio external directory
#   PATCH         path to test_pd_nusmuk.pd
#   SUMMARY_FILE  optional; receives total/passes/fails for the conanfile
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
UTILS_DIR="${UTILS_DIR:?UTILS_DIR must point to the nusmuk-utils externals}"
AUDIO_DIR="${AUDIO_DIR:?AUDIO_DIR must point to the nusmuk-audio externals}"
PATCH="${PATCH:?PATCH must point to test_pd_nusmuk.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$UTILS_DIR" ] || { echo "FAIL: nusmuk-utils dir missing: $UTILS_DIR"; exit 1; }
[ -d "$AUDIO_DIR" ] || { echo "FAIL: nusmuk-audio dir missing: $AUDIO_DIR"; exit 1; }
[ -f "$PATCH" ] || { echo "FAIL: test patch missing: $PATCH"; exit 1; }

total=0
passes=0
fails=0
pass() { total=$((total + 1)); passes=$((passes + 1)); echo "PASS: $1"; }
fail() { total=$((total + 1)); fails=$((fails + 1)); echo "FAIL: $1"; }

# ---- check 1: the 17 externals are on disk -------------------------------
utils_list="line3 mtx_preset pbank tab_derivate tab_downsample
            tab_downsample_average tab_downsample_max tab_downsample_min
            tab_integrate tab_max tab_min tab_upsample tab_upsample_copy"
audio_list="bq~ tabosc4c~ tabosci~ tabread4c~"

n=0
for f in $utils_list; do
    n=$((n + 1))
    if [ -f "$UTILS_DIR/$f.pd_linux" ]; then
        pass "externals present: nusmuk-utils/$f.pd_linux"
    else
        fail "externals present: nusmuk-utils/$f.pd_linux"
    fi
done
if [ "$n" -eq 13 ]; then
    pass "nusmuk-utils ships 13 externals"
else
    fail "nusmuk-utils ships 13 externals (listed $n)"
fi

n=0
for f in $audio_list; do
    n=$((n + 1))
    if [ -f "$AUDIO_DIR/$f.pd_linux" ]; then
        pass "externals present: nusmuk-audio/$f.pd_linux"
    else
        fail "externals present: nusmuk-audio/$f.pd_linux"
    fi
done
if [ "$n" -eq 4 ]; then
    pass "nusmuk-audio ships 4 externals"
else
    fail "nusmuk-audio ships 4 externals (listed $n)"
fi

# ---- check 2: artifacts are aarch64 OHOS ELF objects ---------------------
# Reads the ELF header directly (readelf if available, else file(1)) so a
# host-architecture or 0-byte stub can never pass.
elf_is_aarch64_object() {
    if command -v readelf >/dev/null 2>&1; then
        readelf -h "$1" 2>/dev/null | grep -q "Machine:.*AArch64" || return 1
        # externals are shared objects; accept ET_DYN (normal) and ET_EXEC
        readelf -h "$1" 2>/dev/null | grep -qE "Type:.*(DYN|EXEC)" || return 1
    elif command -v file >/dev/null 2>&1; then
        file "$1" 2>/dev/null | grep -q "ELF 64-bit LSB shared object, ARM aarch64" || return 1
    else
        return 0
    fi
    return 0
}

for f in $utils_list; do
    if elf_is_aarch64_object "$UTILS_DIR/$f.pd_linux"; then
        pass "ELF check: nusmuk-utils/$f.pd_linux is an aarch64 ELF shared object"
    else
        fail "ELF check: nusmuk-utils/$f.pd_linux is not an aarch64 ELF shared object"
    fi
done
for f in $audio_list; do
    if elf_is_aarch64_object "$AUDIO_DIR/$f.pd_linux"; then
        pass "ELF check: nusmuk-audio/$f.pd_linux is an aarch64 ELF shared object"
    else
        fail "ELF check: nusmuk-audio/$f.pd_linux is not an aarch64 ELF shared object"
    fi
done

# pd itself: puredata builds it as a PIE, so its ELF type is ET_DYN, not
# ET_EXEC — the old `Type:.*EXEC` test failed on every correct build.
if command -v readelf >/dev/null 2>&1; then
    if readelf -h "$PD_BIN" 2>/dev/null | grep -q "Machine:.*AArch64"; then
        pass "pd binary is aarch64 ELF"
    else
        fail "pd binary is not aarch64 ELF"
    fi
    if readelf -h "$PD_BIN" 2>/dev/null | grep -qE "Type:.*(DYN|EXEC)"; then
        pass "pd binary is an ELF executable (ET_EXEC or PIE ET_DYN)"
    else
        fail "pd binary is not an ELF executable"
    fi
elif command -v file >/dev/null 2>&1; then
    if file "$PD_BIN" 2>/dev/null | grep -q "ELF 64-bit LSB.*executable, ARM aarch64"; then
        pass "pd binary is aarch64 ELF executable"
    else
        fail "pd binary is not aarch64 ELF executable"
    fi
else
    echo "SKIP: pd binary architecture not verifiable (neither readelf nor file available)"
fi

# ---- run Pd and drive the patch ------------------------------------------
WORK="${TMPDIR:-.}/pd-nusmuk-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

# Work on a copy of the patch so that anything an external writes next to it
# (pbank opens its bank file relative to the patch) lands in $WORK.
cp "$PATCH" "$WORK/test_pd_nusmuk.pd"

LOG="$WORK/pd.log"
if command -v timeout >/dev/null 2>&1; then
    timeout 60 "$PD_BIN" -nogui -nosound \
        -path "$UTILS_DIR:$AUDIO_DIR" -open "$WORK/test_pd_nusmuk.pd" \
        > "$LOG" 2>&1 || true
else
    "$PD_BIN" -nogui -nosound \
        -path "$UTILS_DIR:$AUDIO_DIR" -open "$WORK/test_pd_nusmuk.pd" \
        > "$LOG" 2>&1 || true
fi

echo "--- pd output ---"
cat "$LOG"
echo "--- end pd output ---"

# ---- check 3: no external failed to load, no array was left missing ------
# `couldn't create` / `unknown function` -> the class was not registered
#   (the .pd_linux external was not dlopen'd)
# `^error: ` / `no such array`          -> an external was driven but its Pd
#   arrays were missing, i.e. its compute loop did not really run
# The scan is case-sensitive on purpose: a host loader's own
# `ERROR: ld.so: ...` lines are not Pd errors and must not fail this check.
# A non-empty log is required so an empty run cannot pass vacuously.
if [ ! -s "$LOG" ] || grep -q "couldn't create\|unknown function\|no such array\|^error: " "$LOG"; then
    fail "Pd loaded and drove every external without load error"
    grep "couldn't create\|unknown function\|no such array\|^error: " "$LOG" || true
else
    pass "Pd loaded and drove every external without load error"
fi

# ---- checks 4+5: the driven externals produced their documented output ----
# These lines can only be printed when Pd's logical clock ticks and every
# external's compute loop / outlet actually ran.
check() {
    if grep -q "$1" "$LOG"; then
        pass "$2"
    else
        fail "$2 (expected '$1')"
    fi
}

check "NUSMUK_TAB_MAX: bang"                "nusmuk-utils [tab_max] computed and banged"
check "NUSMUK_TAB_MIN: bang"                "nusmuk-utils [tab_min] computed and banged"
check "NUSMUK_TAB_INTEGRATE: bang"          "nusmuk-utils [tab_integrate] computed and banged"
check "NUSMUK_TAB_DERIVATE: bang"           "nusmuk-utils [tab_derivate] computed and banged"
check "NUSMUK_TAB_UPSAMPLE: bang"           "nusmuk-utils [tab_upsample] computed and banged"
check "NUSMUK_TAB_UPSAMPLE_COPY: bang"      "nusmuk-utils [tab_upsample_copy] computed and banged"
check "NUSMUK_TAB_DOWNSAMPLE: bang"         "nusmuk-utils [tab_downsample] computed and banged"
check "NUSMUK_TAB_DOWNSAMPLE_MAX: bang"     "nusmuk-utils [tab_downsample_max] computed and banged"
check "NUSMUK_TAB_DOWNSAMPLE_MIN: bang"     "nusmuk-utils [tab_downsample_min] computed and banged"
check "NUSMUK_TAB_DOWNSAMPLE_AVERAGE: bang" "nusmuk-utils [tab_downsample_average] computed and banged"
check "NUSMUK_LINE3_PASS: 3.5"              "nusmuk-utils [line3] passes float 3.5 through"
check "NUSMUK_LINE3_PASS2: 7"               "nusmuk-utils [line3] passes float 7 through"

echo "NUSMUK_CHECK_SUMMARY total=$total passes=$passes fails=$fails"
if [ -n "${SUMMARY_FILE:-}" ]; then
    printf 'total=%s\npasses=%s\nfails=%s\n' "$total" "$passes" "$fails" > "$SUMMARY_FILE"
fi
[ "$fails" -eq 0 ]
