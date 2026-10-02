#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for langford 0.0.20130228 (installed userspace tools).
#
# Env:
#   LANG_UTIL  path to the installed langford_util executable
#   ADC_UTIL   path to the installed langford_adc_util executable
#   FSYNTH     path to the installed langford_rf_fsynth executable
#   VGA        path to the installed langford_rx_rf_bb_vga executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

LANG_UTIL="${LANG_UTIL:?LANG_UTIL must point to the installed langford_util}"
ADC_UTIL="${ADC_UTIL:?ADC_UTIL must point to the installed langford_adc_util}"
FSYNTH="${FSYNTH:?FSYNTH must point to the installed langford_rf_fsynth}"
VGA="${VGA:?VGA must point to the installed langford_rx_rf_bb_vga}"

WORK="${TMPDIR:-.}/langford-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

checks=0
fails=0

check() { # check <name> <actual> <expected> [dumpfile]
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		if [ -n "${4:-}" ] && [ -f "$4" ]; then
			echo "--- $4 ---"; head -20 "$4"; echo "--- end ---"
		fi
		fails=$((fails + 1))
	fi
}

# 1-2. langford_util with no arguments prints usage and fails
"$LANG_UTIL" > u.out 2> u.err && rc=0 || rc=$?
check "langford_util (no args) exits 1" "$rc" 1
check "langford_util prints usage" "$(grep -c -F 'Usage:' u.err)" 1

# 3-4. langford_util on a missing device: the ioctl fails, so it exits non-zero
"$LANG_UTIL" /nonexistent-langford N21at0 > d.out 2> d.err && rc=0 || rc=$?
if [ "$rc" -ne 0 ]; then nz=nonzero; else nz=zero; fi
check "langford_util (missing device) exits non-zero" "$nz" nonzero
check "langford_util handled the pin command" "$(grep -c -F 'is set to' d.out)" 1

# 5-6. langford_adc_util with no arguments prints usage and fails
"$ADC_UTIL" > a.out 2> a.err && rc=0 || rc=$?
check "langford_adc_util (no args) exits 1" "$rc" 1
check "langford_adc_util prints usage" "$(grep -c -F 'Usage:' a.err)" 1

# 7-8. langford_adc_util on a missing device: the SPI ioctls fail, exit non-zero
"$ADC_UTIL" /nonexistent-langford A Raw 0x123 > b.out 2> b.err && rc=0 || rc=$?
if [ "$rc" -ne 0 ]; then nz=nonzero; else nz=zero; fi
check "langford_adc_util (missing device) exits non-zero" "$nz" nonzero
check "langford_adc_util wrote the SPI frame" "$(grep -c -F 'Writing SPI value' b.out)" 1

# 9-10. langford_rf_fsynth with no arguments prints usage and fails
"$FSYNTH" > f.out 2> f.err && rc=0 || rc=$?
check "langford_rf_fsynth (no args) exits 1" "$rc" 1
check "langford_rf_fsynth prints usage" "$(grep -c -F 'Usage:' f.err)" 1

# 11-12. langford_rf_fsynth rejects an invalid channel
"$FSYNTH" /nonexistent-langford bogus 100000000 > fc.out 2> fc.err && rc=0 || rc=$?
check "langford_rf_fsynth (bad channel) exits 1" "$rc" 1
check "langford_rf_fsynth reports bad channel" "$(grep -c -F 'Invalid Channel Selection' fc.err)" 1

# 13-14. langford_rx_rf_bb_vga with no arguments prints usage and fails
"$VGA" > v.out 2> v.err && rc=0 || rc=$?
check "langford_rx_rf_bb_vga (no args) exits 1" "$rc" 1
check "langford_rx_rf_bb_vga prints usage" "$(grep -c -F 'Usage:' v.err)" 1

# 15-16. langford_rx_rf_bb_vga rejects an out-of-range gain
"$VGA" /nonexistent-langford 0 99 > vg.out 2> vg.err && rc=0 || rc=$?
check "langford_rx_rf_bb_vga (bad gain) exits 1" "$rc" 1
check "langford_rx_rf_bb_vga reports invalid gain" "$(grep -c -F 'Invalid Gain' vg.err)" 1

echo "LANGFORD_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
