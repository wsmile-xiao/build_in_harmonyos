#!/bin/bash
# Functional consumer test for iverilog: compile a tiny design, then simulate it with vvp.
# Usage: test.sh <package_folder>
set -euo pipefail
ROOT="$1"
BIN="$ROOT/bin"
BASE="$ROOT/lib/ivl"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

cat > "$TMP/hello.v" <<'VERILOG'
module main;
  reg [7:0] value;
  initial begin
    value = 8'hA5;
    $display("IVERILOG_OK %0d", value);
    $finish;
  end
endmodule
VERILOG

# -B points at the relocated IVL modules: conan installs with --prefix=/ + DESTDIR,
# so the compiled-in module path (/lib/ivl) does not match the package folder.
"$BIN/iverilog" -B"$BASE" -o "$TMP/hello.vvp" "$TMP/hello.v"

OUT=$("$BIN/vvp" "$TMP/hello.vvp")
printf '%s\n' "$OUT"
# vvp also prints a trailing "$finish called at ..." line, so match the expected line.
printf '%s\n' "$OUT" | grep -q '^IVERILOG_OK 165$' || {
    echo "FAIL: unexpected vvp output: $OUT" >&2
    exit 1
}
echo "PASS: iverilog compiled the design and vvp produced the expected result"
