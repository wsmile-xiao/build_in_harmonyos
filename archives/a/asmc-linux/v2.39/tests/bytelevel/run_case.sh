#!/bin/sh
# r217 byte-level regression harness for asmc-linux v2.39
#
# For each case:
#   cases/<name>.asm  -> asmc format source (assembled by asmc_native)
#   cases/<name>.s    -> AT&T x86-64 source (assembled by clang -target x86_64-linux-gnu)
# Expected bytes come from clang/LLVM (trusted local reference assembler) disassembled
# by llvm-objdump; actual bytes come from asmc_native -> llvm-objdump. Only instruction
# bytes matter (addresses/symbols normalized). Red = actual != expected.
#
# Usage: ./run_case.sh <name> [workdir]
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
ASMC="/storage/Users/currentUser/junshi_liu/worktrees/pc3-5-asmc-linux-v2.39/archives/a/asmc-linux/v2.39/source/asmc_native"
OBJDUMP=/data/service/hnp/bin/llvm-objdump
CLANG="clang -target x86_64-linux-gnu -c"
CASES="$BASE/cases"
WORK="${2:-$BASE/work}"
name="$1"
mkdir -p "$WORK"

# --- reference: clang -> .o -> disassembly (bytes only) ---
if ! $CLANG "$CASES/$name.s" -o "$WORK/${name}_ref.o" 2>"$WORK/${name}_ref.err"; then
  echo "CASE $name: REF-ASSEMBLE-FAIL"; exit 2
fi
extract_bytes() {
  $OBJDUMP -d "$1" 2>/dev/null | awk '
    /Disassembly/ { dis=1 }
    dis && /^[[:space:]]*[0-9a-f]+:/ {
      line=$0
      sub(/^[[:space:]]*[0-9a-f]+:[[:space:]]*/, "", line)
      sub(/\t.*/, "", line)   # drop mnemonic/comment after the TAB; keep space-separated bytes
      sub(/[[:space:]]+$/, "", line)  # trim trailing spaces left before the TAB
      if (line ~ /^[0-9a-f]{2}( [0-9a-f]{2})*$/) print line
    }'
}
extract_bytes "$WORK/${name}_ref.o" > "$WORK/${name}_ref.bytes"

# --- actual: asmc_native -> .o -> disassembly (bytes only) ---
# asmc writes <basename>.o/.bin next to the source file; collect from cases dir.
rm -f "$CASES/${name}.o" "$CASES/${name}.bin"
(cd "$CASES" && "$ASMC" "$name.asm" >"$WORK/${name}_asmc.log" 2>&1 || true)
if [ -f "$CASES/${name}.o" ]; then
  mv -f "$CASES/${name}.o" "$WORK/${name}_act.o"
fi
if [ ! -f "$WORK/${name}_act.o" ]; then
  echo "CASE $name: ASMC-NO-OUTPUT"
  echo "--- asmc log ---"; cat "$WORK/${name}_asmc.log" 2>/dev/null
  exit 2
fi
rm -f "$CASES/${name}.bin"
extract_bytes "$WORK/${name}_act.o" > "$WORK/${name}_act.bytes"

if diff -q "$WORK/${name}_ref.bytes" "$WORK/${name}_act.bytes" >/dev/null 2>&1; then
  echo "CASE $name: GREEN (bytes match)"
  exit 0
else
  echo "CASE $name: RED (mismatch)"
  echo "--- expected ---"; cat "$WORK/${name}_ref.bytes"
  echo "--- actual ---";   cat "$WORK/${name}_act.bytes"
  exit 1
fi
