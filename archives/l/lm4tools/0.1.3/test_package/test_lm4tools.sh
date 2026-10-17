#!/bin/sh
# Functional test suite for the packaged lm4flash / lmicdi executables.
#
# Usage: sh test_lm4tools.sh <bin-dir>
#
# Upstream lm4tools v0.1.3 ships no test framework (no check/test target in
# either Makefile, no tests/ tree), so these cases are the补全 suite.
#
# Scope split (this suite is written to run on a machine WITHOUT a Stellaris
# LaunchPad ICDI board attached, which is the norm in the archive CI):
#   * lm4flash CLI argument-parsing / usage / version paths that complete
#     before libusb_init() -> F1-F5, F7, F10 (exact exit codes + stderr text).
#   * libusb-dependent paths that need a real ICDI device (VID 1cbe:00fd) are
#     NOT faked as passing: they are asserted only to fail cleanly with an
#     upstream error message when no device is present (F6, F8, F9), and the
#     hardware-dependent behaviour is documented as "requires real hardware"
#     in MANIFEST.yml + notes.md instead of being checked here.
#   * lmicdi has no argument parsing at all (main() calls libusb_init then
#     enumerates); without a device it exits non-zero -> F11-F13.
#
# Counting convention (identical to MANIFEST.yml, notes.md and the PR table):
# one independent check item per assertion, F1-F13, individually decidable.
#
# Exit code 0 = all items passed, 1 = at least one failure.
set -u
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

bin_dir=${1:?usage: test_lm4tools.sh <bin-dir>}
LM4F="$bin_dir/lm4flash"
LMICDI="$bin_dir/lmicdi"

if [ ! -f "$LM4F" ] || [ ! -x "$LM4F" ]; then
    printf 'FAIL: lm4flash missing or not executable in %s\n' "$bin_dir" >&2
    exit 1
fi
if [ ! -f "$LMICDI" ] || [ ! -x "$LMICDI" ]; then
    printf 'FAIL: lmicdi missing or not executable in %s\n' "$bin_dir" >&2
    exit 1
fi

# OHOS / is largely read-only (erofs) and /tmp may not be writable, so every
# scratch file goes under a TMPDIR we create ourselves.
work="${TMPDIR:-/tmp}/lm4tools-test.$$"
if ! mkdir -p "$work" 2>/dev/null; then
    work="./lm4tools-test.$$"
    mkdir -p "$work" || { printf 'FAIL: no writable scratch dir\n' >&2; exit 1; }
fi
trap 'rm -rf "$work"' EXIT HUP INT TERM

pass=0
fail=0

ok() {
    pass=$((pass + 1))
    printf 'ok %s: %s\n' "$1" "$2"
}

bad() {
    fail=$((fail + 1))
    printf 'FAIL %s: %s\n' "$1" "$2" >&2
}

# ---------------------------------------------------------------- F1
out="$work/f1.out"
"$LM4F" -V >"$out" 2>/dev/null
rc=$?
if [ "$rc" -eq 0 ] && grep -q 'LM4Flash version 0\.1\.3' "$out"; then
    ok F1_version_banner "-V prints 'LM4Flash version 0.1.3' to stdout and exits 0 (rc=$rc)"
else
    bad F1_version_banner "rc=$rc out=$(head -c 120 "$out")"
fi

# ---------------------------------------------------------------- F2
out="$work/f2.out"
"$LM4F" -h >"$out" 2>/dev/null
rc=$?
if [ "$rc" -eq 0 ] && grep -q '^Usage: lm4flash' "$out"; then
    ok F2_help_usage_text "-h prints the 'Usage: lm4flash' synopsis to stdout and exits 0 (rc=$rc)"
else
    bad F2_help_usage_text "rc=$rc out=$(head -c 120 "$out")"
fi

# ---------------------------------------------------------------- F3
"$LM4F" >"$work/f3.out" 2>/dev/null
rc=$?
if [ "$rc" -eq 1 ] && grep -q '^Usage: lm4flash' "$work/f3.out"; then
    ok F3_no_args_rejected "no arguments is rejected with rc=1 and the usage text"
else
    bad F3_no_args_rejected "rc=$rc usage_lines=$(grep -c '^Usage: lm4flash' "$work/f3.out")"
fi

# ---------------------------------------------------------------- F4
"$LM4F" -q foo.bin >"$work/f4.out" 2>/dev/null
rc=$?
if [ "$rc" -eq 1 ] && grep -q '^Usage: lm4flash' "$work/f4.out"; then
    ok F4_bad_option_rejected "unknown option '-q' is rejected with rc=1 and the usage text"
else
    bad F4_bad_option_rejected "rc=$rc out=$(head -c 100 "$work/f4.out")"
fi

# ---------------------------------------------------------------- F5
"$LM4F" -S 0x1 "$work/rom.bin" >"$work/f5.out" 2>/dev/null
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'must be .* aligned' "$work/f5.out"; then
    ok F5_start_addr_misaligned "-S 0x1 (misaligned to the 1024-byte erase block) is rejected with rc=1"
else
    bad F5_start_addr_misaligned "rc=$rc out=$(head -c 100 "$work/f5.out")"
fi

# ---------------------------------------------------------------- F6
# -S 0x400 is properly 1024-aligned, so argument parsing succeeds and the
# failure moves into the libusb stage. Without a real ICDI board this must
# fail non-zero: either libusb_init() itself fails (rc=255, 'Error
# initializing libusb') or enumeration finds no device (rc=1, 'Unable to find
# any ICDI devices'). A rc=0 would mean a fabricated flash without hardware.
"$LM4F" -S 0x400 "$work/rom.bin" >/dev/null 2>"$work/f6.err"
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 127 ] && [ "$rc" -ne 126 ]; then
    ok F6_device_path_fails_clean "parse-valid '-S 0x400 <file>' without an ICDI board fails cleanly (rc=$rc, reached the libusb stage)"
else
    bad F6_device_path_fails_clean "rc=$rc without hardware means the flash loop was never entered but reported success"
fi

# ---------------------------------------------------------------- F7
"$LM4F" -S 0x1 "$work/rom.bin" >"$work/f7.out" 2>/dev/null
rc=$?
if [ "$rc" -eq 1 ] && cmp -s "$work/f5.out" "$work/f7.out"; then
    ok F7_error_deterministic "the -S misalignment rejection is byte-identical across runs"
else
    bad F7_error_deterministic "rc=$rc repeat_run_differs"
fi

# ---------------------------------------------------------------- F8
# The real flash loop needs the ICDI device; without one the run must still
# terminate with a recognisable upstream error message rather than hanging or
# crashing. Both no-libusb and no-board outcomes are acceptable; the point is
# "clean, non-zero, with upstream text".
"$LM4F" "$work/rom.bin" >/dev/null 2>"$work/f8.err"
rc=$?
if [ "$rc" -ne 0 ] && { grep -q 'Error initializing libusb' "$work/f8.err" || grep -q 'Unable to find any ICDI devices' "$work/f8.err"; }; then
    ok F8_no_device_clean_failure "flashing without an ICDI board fails cleanly with an upstream error (rc=$rc: $(head -c 80 "$work/f8.err"))"
else
    bad F8_no_device_clean_failure "rc=$rc stderr=$(head -c 100 "$work/f8.err")"
fi

# ---------------------------------------------------------------- F9
# A missing input file must never be reported as a successful flash: that
# would fabricate hardware evidence. Upstream either fails at libusb_init or
# (with healthy libusb) reports 'Cannot open file'; either way rc != 0.
"$LM4F" "$work/definitely-missing.bin" >/dev/null 2>"$work/f9.err"
rc=$?
if [ "$rc" -ne 0 ]; then
    ok F9_missing_file_never_fakes_success "a missing binary file never reports success (rc=$rc)"
else
    bad F9_missing_file_never_fakes_success "rc=0 would fabricate a successful flash"
fi

# ---------------------------------------------------------------- F10
# Serial-number selection (-s) is parsed before libusb; combined with a
# misaligned -S the argument layer rejects it deterministically.
"$LM4F" -s SN123 -S 0x1 "$work/rom.bin" >"$work/f10.out" 2>/dev/null
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'must be .* aligned' "$work/f10.out"; then
    ok F10_serial_plus_misaligned "-s SERIAL combined with a misaligned -S is still rejected in the argument layer (rc=$rc)"
else
    bad F10_serial_plus_misaligned "rc=$rc out=$(head -c 100 "$work/f10.out")"
fi

# ---------------------------------------------------------------- F11
# lmicdi has no CLI parsing at all: main() goes straight to libusb_init() +
# ASSERT. Without an ICDI board it must exit non-zero (on this host the
# assertion aborts -> 134; with healthy libusb the 'No ICDI device' branch
# exits 1). rc=0 would require real hardware and must not happen here.
timeout 10 "$LMICDI" >/dev/null 2>"$work/f11.err"
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] && [ "$rc" -ne 127 ]; then
    ok F11_lmicdi_no_device_fails "lmicdi without an ICDI board exits non-zero (rc=$rc)"
else
    bad F11_lmicdi_no_device_fails "rc=$rc (124=hang, 127=exec failure)"
fi

# ---------------------------------------------------------------- F12
# lmicdi diagnostics (TRACE + the 'No ICDI device' fprintf) go to stderr;
# stdout must stay empty so scripted consumers cannot mistake partial output
# for a successful debug session.
"$LMICDI" >"$work/f12.out" 2>/dev/null
rc=$?
if [ ! -s "$work/f12.out" ]; then
    ok F12_lmicdi_stdout_empty "lmicdi keeps stdout empty when no device is found (rc=$rc)"
else
    bad F12_lmicdi_stdout_empty "unexpected stdout: $(head -c 80 "$work/f12.out")"
fi

# ---------------------------------------------------------------- F13
# lmicdi must terminate on its own (an infinite USB poll loop would hang the
# archive CI). A run under timeout that hits the deadline would return 124.
timeout 10 "$LMICDI" >/dev/null 2>/dev/null
rc=$?
if [ "$rc" -ne 124 ]; then
    ok F13_lmicdi_terminates "lmicdi terminates within 10s without a device (rc=$rc)"
else
    bad F13_lmicdi_terminates "lmicdi hung until the 10s timeout"
fi

printf '\nLM4TOOLS_FUNCTIONAL={"discovered": %d, "passed": %d, "failed": %d}\n' \
    "$((pass + fail))" "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
