#!/usr/bin/env bash
set -eu

CRASM_BIN="${CRASM_BIN:-crasm}"
work_root="${TMPDIR:-$PWD}"
work_dir="$work_root/crasm-test-$$"
mkdir -p "$work_dir"
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

asm_file="$work_dir/smoke.6502.asm"
out_file="$work_dir/smoke.srec"
expected_file="$work_dir/expected.srec"
actual_file="$work_dir/actual.srec"

cat > "$asm_file" <<'ASM'
cpu 6502
*=1000H
start lda #1
sta 2000H
jmp start
ASM

cat > "$expected_file" <<'EOF_EXPECTED'
S10B1000A9018D00204C001031
S9030000FC
EOF_EXPECTED

help_output=$("$CRASM_BIN" 2>&1 || true)
case "$help_output" in
  *"Crasm 1.11"*|*"Syntax:  crasm"*) ;;
  *)
    echo "Unexpected help/version output:"
    echo "$help_output"
    exit 1
    ;;
esac

"$CRASM_BIN" -o "$out_file" -l "$asm_file"
tr -d '\r' < "$out_file" > "$actual_file"
diff -u "$expected_file" "$actual_file"

echo "crasm smoke test passed"
