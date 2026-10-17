#!/usr/bin/env bash
# test_package/test.sh — functional tests for the dis51 executable (OHOS aarch64).
#
# Usage: bash test.sh <package_bin_dir> [work_dir]
#
# The binary is taken from the tested package's bin/ directory (never from
# PATH) so that the CI L1e negative test (package artifacts sabotaged and the
# test re-run) really fails when the package is broken.
#
# Scratch files go to $2 when given (the Conan test build folder), otherwise to
# $PWD/dis51-test-work, so that nothing is written next to the test fixtures.
#
# dis51 reads an Intel HEX file from stdin and writes 8051 assembly to stdout,
# so every case here feeds a fixture through the package binary and compares
# the produced assembly against a hand-checked expected listing.
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "[fail] dis51: package bin dir not found: '$BIN_DIR'"
    exit 1
fi

DIS51="$BIN_DIR/dis51"
if [ ! -f "$DIS51" ]; then
    echo "[fail] dis51: binary missing in package: $DIS51"
    exit 1
fi
if [ ! -x "$DIS51" ]; then
    echo "[fail] dis51: binary is not executable: $DIS51"
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
FIX="$HERE/fixtures"
EXP="$HERE/expected"
WORK_DIR="${2:-$PWD/dis51-test-work}"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

TOTAL=0
PASSED=0
FAILED=0

ok() {
    TOTAL=$((TOTAL + 1))
    PASSED=$((PASSED + 1))
    echo "        [ok] $1"
}

ko() {
    TOTAL=$((TOTAL + 1))
    FAILED=$((FAILED + 1))
    echo "        [fail] $1"
    if [ -n "${2:-}" ] && [ -f "$2" ]; then
        sed -n '1,20p' "$2"
    fi
}

# Run the package binary with the given stdin fixture; $1 = fixture, $2.. = args.
# The exit status is stored in RUN_RC, stdout in $WORK_DIR/actual.out,
# stderr in $WORK_DIR/actual.err.
run_dis51() {
    local fixture="$1"
    shift
    set +e
    "$DIS51" "$@" < "$FIX/$fixture" > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
    RUN_RC=$?
    set -e
}

# Compare stdout of the last run against an expected listing.
check_listing() {
    local name="$1"
    local expected="$2"
    if [ "$RUN_RC" -ne 0 ]; then
        ko "$name: exit status $RUN_RC (expected 0)" "$WORK_DIR/actual.err"
        return
    fi
    if diff -u "$EXP/$expected" "$WORK_DIR/actual.out" > "$WORK_DIR/$name.diff" 2>&1; then
        ok "$name: output matches expected/$expected"
    else
        ko "$name: output differs from expected/$expected" "$WORK_DIR/$name.diff"
    fi
}

echo "[step] dis51 test_package: running against $DIS51"

# ── Case 1: --version ────────────────────────────────────────────────────────
set +e
VERSION_OUT="$("$DIS51" --version < /dev/null 2>&1)"
VERSION_RC=$?
set -e
if [ "$VERSION_RC" -eq 0 ] && [ "$VERSION_OUT" = "Dis51 0.5 - 8051 Intel Hex disassembler" ]; then
    ok "version_flag: '$VERSION_OUT'"
else
    ko "version_flag: rc=$VERSION_RC out='$VERSION_OUT'"
fi

# ── Case 2: --help ───────────────────────────────────────────────────────────
set +e
"$DIS51" --help < /dev/null > "$WORK_DIR/help.out" 2>&1
HELP_RC=$?
set -e
if [ "$HELP_RC" -eq 0 ] && grep -q 'Usage: dis51 \[-l\] \[entry point \.\.\.\]' "$WORK_DIR/help.out"; then
    ok "help_flag: usage line present"
else
    ko "help_flag: rc=$HELP_RC" "$WORK_DIR/help.out"
fi

# ── Case 3: basic control flow, default entry point 0 ────────────────────────
run_dis51 basic.hex
check_listing "basic_default" "basic.default.asm"

# ── Case 4: SFR / bit-address symbolic decoding ──────────────────────────────
run_dis51 sfr.hex
check_listing "sfr_default" "sfr.default.asm"

# ── Case 5: ALU, rotate, stack and external-memory opcodes ───────────────────
run_dis51 alu.hex
check_listing "alu_default" "alu.default.asm"

# ── Case 6: branches, calls and code segments (default entry point 0) ────────
run_dis51 flow.hex
check_listing "flow_default" "flow.default.asm"

# ── Case 7: same firmware disassembled from entry point 16 (0x0010) ──────────
run_dis51 flow.hex 16
check_listing "flow_entry16" "flow.entry16.asm"

# ── Case 8: -l listing format (address + bytes + ASCII comment) ──────────────
run_dis51 basic.hex -l
check_listing "basic_listing" "basic.listing.txt"

# ── Case 9: the unreached regions become data and new segments ───────────────
run_dis51 flow.hex
SEGMENTS_RC=0
grep -q '^CSEG AT 0010h$' "$WORK_DIR/actual.out" || SEGMENTS_RC=1
grep -q '^CSEG AT 0040h$' "$WORK_DIR/actual.out" || SEGMENTS_RC=1
grep -q 'DB 04h' "$WORK_DIR/actual.out" || SEGMENTS_RC=1
if [ "$RUN_RC" -eq 0 ] && [ "$SEGMENTS_RC" -eq 0 ]; then
    ok "flow_segments: CSEG AT 0010h/0040h and DB 04h present"
else
    ko "flow_segments: missing segment or data directive" "$WORK_DIR/actual.out"
fi

# ── Case 10: illegal opcode A5 is reported and does not abort ────────────────
run_dis51 illegal.hex
if [ "$RUN_RC" -ne 0 ]; then
    ko "illegal_opcode: exit status $RUN_RC (expected 0)"
elif ! grep -q 'Illegal opcode A5 at address 0000' "$WORK_DIR/actual.err"; then
    ko "illegal_opcode: diagnostic missing on stderr" "$WORK_DIR/actual.err"
elif diff -u "$EXP/illegal.default.asm" "$WORK_DIR/actual.out" > "$WORK_DIR/illegal_opcode.diff" 2>&1; then
    ok "illegal_opcode: diagnostic on stderr and 'DB 85h  ; illegal opcode' emitted"
else
    ko "illegal_opcode: output differs from expected/illegal.default.asm" "$WORK_DIR/illegal_opcode.diff"
fi

# ── Case 11: a corrupt Intel HEX file is rejected ────────────────────────────
printf 'this is not an intel hex file\n' > "$WORK_DIR/bad.hex"
set +e
"$DIS51" < "$WORK_DIR/bad.hex" > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
BAD_RC=$?
set -e
if [ "$BAD_RC" -ne 0 ] && grep -q 'Error reading hex file.' "$WORK_DIR/actual.err"; then
    ok "invalid_hex_rejected: exit status $BAD_RC with 'Error reading hex file.'"
else
    ko "invalid_hex_rejected: rc=$BAD_RC" "$WORK_DIR/actual.err"
fi

# ── Case 12: empty input is rejected ─────────────────────────────────────────
set +e
"$DIS51" < /dev/null > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
EMPTY_RC=$?
set -e
if [ "$EMPTY_RC" -ne 0 ]; then
    ok "empty_input_rejected: exit status $EMPTY_RC"
else
    ko "empty_input_rejected: exit status 0 (expected non-zero)"
fi

echo "[step] dis51 test_package summary: TOTAL=$TOTAL PASS=$PASSED FAIL=$FAILED"
if [ "$TOTAL" -eq 0 ] || [ "$FAILED" -ne 0 ]; then
    echo "[fail] dis51 test_package: $FAILED of $TOTAL cases failed"
    exit 1
fi
echo "[ok] dis51 test_package: all $TOTAL cases passed"
