#!/usr/bin/env bash
# test_package/test.sh — behaviour contract for the installed yell CLI.
#
# Usage: test.sh <path-to-installed-yell-binary>
#
# yell plays a short tune on the PC speaker by writing an ASCII tune string
# to /dev/speaker.  On OHOS there is no PC speaker device, so the documented
# runtime contract is *graceful degradation*: play()'s open("/dev/speaker")
# fails, nothing is written, nothing is printed, and main() still returns
# EXIT_SUCCESS (yell.c: open() result is guarded by `if (handle >= 0)`).
#
# Check list (each is a counted assertion; the script exits non-zero on the
# first failure):
#   T1  installed binary exists, is a regular file and is executable
#   T2  ELF64 object for the aarch64 machine (readelf -h)
#   T3  the only DT_NEEDED entry is libc.so (readelf -d, pure C binary)
#   T4  running the CLI exits 0 (graceful degradation without /dev/speaker)
#   T5  running the CLI produces no output at all (no diagnostics expected)
#   T6  second invocation is idempotent: exit 0 again (no state, no crash)
set -euo pipefail

BIN="${1:?usage: test.sh <installed-yell-binary>}"
readelf="${READELF:-readelf}"

fail() { echo "test_package FAIL: $*" >&2; exit 1; }
pass() { echo "test_package PASS: $*"; }

# T1 — installed binary exists, regular file, executable bit set
[ -f "$BIN" ] || fail "T1 $BIN is not a regular file"
[ -x "$BIN" ] || fail "T1 $BIN is not executable"
pass "T1 installed binary present and executable"

# T2 — ELF64 / AArch64
elf_class="$("$readelf" -h "$BIN" | sed -n 's/^  Class:[[:space:]]*//p')"
elf_mach="$("$readelf" -h "$BIN" | sed -n 's/^  Machine:[[:space:]]*//p')"
[ "$elf_class" = "ELF64" ] || fail "T2 unexpected ELF class: $elf_class"
[ "$elf_mach" = "AArch64" ] || fail "T2 unexpected machine: $elf_mach"
pass "T2 ELF64 AArch64 binary"

# T3 — DT_NEEDED must be exactly [libc.so] (pure C, no libc++/libm deps)
needed="$("$readelf" -d "$BIN" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')"
[ "$needed" = "libc.so" ] || fail "T3 unexpected DT_NEEDED: $needed"
pass "T3 DT_NEEDED is exactly libc.so"

# T4 — run: exit 0 (no speaker device required for a clean exit)
rc=0
out="$("$BIN" 2>&1)" || rc=$?
[ "$rc" -eq 0 ] || fail "T4 exit code $rc (expected 0)"
pass "T4 run exits 0 without a speaker device"

# T5 — and the same run must have produced no output
[ -z "$out" ] || fail "T5 unexpected output: $out"
pass "T5 run produces no output"

# T6 — idempotent second run: exit 0 again (no state, no crash)
rc=0
"$BIN" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] || fail "T6 second run exit code $rc (expected 0)"
pass "T6 second run exits 0 (idempotent)"

echo "test_package: all 6 checks passed for $BIN"
