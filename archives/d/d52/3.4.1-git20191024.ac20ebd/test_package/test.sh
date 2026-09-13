#!/bin/sh
# test_package/test.sh — real behavior tests for the installed d52/d48/dz80 binaries.
#
# Usage: sh test.sh <data-dir> <work-dir>
#
# The script only uses POSIX sh constructs and utilities available on OHOS
# (no bash arrays, no [[ ]], no process substitution). Verified on this device's
# /bin/sh, which is MirBSD KSH R59 (mksh) — not toybox ash; note that
# /proc/self/exe reported from an external command points at that command, not
# at the shell, so it must not be used to identify the shell. Also re-verified
# under busybox ash 1.37.0, with byte-identical results.
#
# Assertions (15 total):
#   1-3  self-identification of all three disassemblers (installed binaries run)
#   4-10 d52 golden replay: upstream cycle files -> upstream expected .d52 output
#   11   dz80 golden replay (binary input + -d option)
#   12   d52 error handling for a missing input file
#   13   d48 real disassembly of the same Intel HEX input
#   14   d52 -u upper-case output mode
#   15   d52 -t trace/analyze mode (generates a control file, then disassembles)
set -u

DATA_DIR=${1:?usage: sh test.sh <data-dir> <work-dir>}
WORK_DIR=${2:?usage: sh test.sh <data-dir> <work-dir>}

PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); echo "PASS: $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }

D52_BIN=$(command -v d52 2>/dev/null || true)
D48_BIN=$(command -v d48 2>/dev/null || true)
DZ80_BIN=$(command -v dz80 2>/dev/null || true)
if [ -z "$D52_BIN" ] || [ -z "$D48_BIN" ] || [ -z "$DZ80_BIN" ]; then
	echo "FAIL: installed binaries not found on PATH (d52='$D52_BIN' d48='$D48_BIN' dz80='$DZ80_BIN')"
	exit 1
fi
echo "binaries: d52=$D52_BIN d48=$D48_BIN dz80=$DZ80_BIN"

# Every run happens inside WORK_DIR so the package source tree stays untouched.
RUN_DIR="$WORK_DIR/run"
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR" || { echo "FAIL: cannot create $RUN_DIR"; exit 1; }
cp -R "$DATA_DIR"/. "$RUN_DIR"/ || { echo "FAIL: cannot stage fixtures"; exit 1; }

# The Z80 input fixture is stored as printable text (z.bin.esc: one POSIX '\ooo'
# octal escape per byte) instead of a raw .bin, so that both the archive and the
# platform-generated PR diff stay text-only — a raw binary added by a PR cannot be
# applied by the CI checkout step ("missing binary patch data"). Rebuild the exact
# 39-byte upstream file here; its correctness is proven end-to-end by the dz80
# golden replay below (any wrong byte changes the disassembly and fails the
# byte-for-byte comparison against upstream z.z80).
Z80_ESC="$DATA_DIR/z.bin.esc"
Z80_BIN="$RUN_DIR/z.bin"
if [ ! -s "$Z80_ESC" ]; then
	echo "FAIL: missing fixture $Z80_ESC"
	exit 1
fi
# '%b' (not a bare format string) so the file content is only ever an argument
# that gets its escape sequences expanded — it can never be interpreted as a
# printf conversion specification. Verified byte-identical to the upstream
# 39-byte file on device under /bin/sh (MirBSD KSH R59) and under busybox ash.
printf '%b' "$(cat "$Z80_ESC")" >"$Z80_BIN" || { echo "FAIL: cannot rebuild z.bin from $Z80_ESC"; exit 1; }
Z80_SIZE=$(wc -c <"$Z80_BIN")
if [ "$Z80_SIZE" != "39" ]; then
	echo "FAIL: rebuilt z.bin is $Z80_SIZE bytes, expected 39 (upstream z.bin)"
	exit 1
fi
echo "fixture: rebuilt z.bin from z.bin.esc ($Z80_SIZE bytes, upstream sha256 9479e071...db55)"

# ── 1-3: self-identification (each binary really starts and reports V3.4.1) ──
"$D52_BIN" >"$WORK_DIR/d52-usage.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "D52 8052 Disassembler V3.4.1" "$WORK_DIR/d52-usage.out"; then
	ok "d52 runs and self-identifies as 'D52 8052 Disassembler V3.4.1'"
else
	bad "d52 self-identification (rc=$rc)"
fi

"$D48_BIN" >"$WORK_DIR/d48-usage.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "D48 8048/8041 Disassembler V 3.4.1" "$WORK_DIR/d48-usage.out"; then
	ok "d48 runs and self-identifies as 'D48 8048/8041 Disassembler V 3.4.1'"
else
	bad "d48 self-identification (rc=$rc)"
fi

"$DZ80_BIN" >"$WORK_DIR/dz80-usage.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "DZ80 Z80/8080/8085 Disassembler V 3.4.1" "$WORK_DIR/dz80-usage.out"; then
	ok "dz80 runs and self-identifies as 'DZ80 Z80/8080/8085 Disassembler V 3.4.1'"
else
	bad "dz80 self-identification (rc=$rc)"
fi

# ── 4-10: d52 golden replay against upstream-cycle-file expected output ──
# Upstream ships benchmark program BENCH0.HEX plus one expected disassembly per
# MCU derivative (cyclefiles/bench0.<derivative>.d52). Only the 4-line
# version/date header is allowed to differ (version 3.4.1 prints y/m/d).
for cyc in ADuC84x AT89LP DS80C320 DS89C4x0 MSC12xx SiLabs W77e; do
	lower=$(printf '%s' "$cyc" | tr 'A-Z' 'a-z')
	exp="$DATA_DIR/bench0.$lower.d52"
	got="$WORK_DIR/got-$lower.d52"
	log="$WORK_DIR/d52-$cyc.log"
	rm -f "$RUN_DIR/bench0.d52" "$got"
	( cd "$RUN_DIR" && "$D52_BIN" -z"$cyc".cyc bench0 >"$log" 2>&1 )
	rc=$?
	if [ "$rc" -ne 0 ] || [ ! -s "$RUN_DIR/bench0.d52" ]; then
		bad "d52 golden replay $cyc (rc=$rc, output missing/empty)"
		continue
	fi
	tail -n +5 "$RUN_DIR/bench0.d52" >"$got"
	tail -n +5 "$exp" >"$WORK_DIR/exp-$lower.d52"
	if [ ! -s "$got" ] || [ ! -s "$WORK_DIR/exp-$lower.d52" ]; then
		bad "d52 golden replay $cyc (empty comparison input)"
		continue
	fi
	if cmp -s "$got" "$WORK_DIR/exp-$lower.d52" && grep -q "org" "$got" && grep -q "end" "$got"; then
		ok "d52 golden replay $cyc: $(wc -l <"$got") lines byte-identical to upstream bench0.$lower.d52 (cycle counts included)"
	else
		bad "d52 golden replay $cyc (output differs from upstream bench0.$lower.d52)"
		diff "$WORK_DIR/exp-$lower.d52" "$got" | head -20
	fi
done

# ── 11: dz80 golden replay (binary input, -d address/data comments) ──
rm -f "$RUN_DIR/z.z80" "$WORK_DIR/got-z80.z80"
( cd "$RUN_DIR" && "$DZ80_BIN" -d z >"$WORK_DIR/dz80-z.log" 2>&1 )
rc=$?
if [ "$rc" -ne 0 ] || [ ! -s "$RUN_DIR/z.z80" ]; then
	bad "dz80 golden replay (rc=$rc, output missing/empty)"
else
	tail -n +5 "$RUN_DIR/z.z80" >"$WORK_DIR/got-z80.z80"
	tail -n +5 "$DATA_DIR/z.z80" >"$WORK_DIR/exp-z80.z80"
	if [ -s "$WORK_DIR/got-z80.z80" ] && cmp -s "$WORK_DIR/got-z80.z80" "$WORK_DIR/exp-z80.z80"; then
		ok "dz80 golden replay: $(wc -l <"$WORK_DIR/got-z80.z80") lines byte-identical to upstream z.z80 (cycle counts included)"
	else
		bad "dz80 golden replay (output differs from upstream z.z80)"
		diff "$WORK_DIR/exp-z80.z80" "$WORK_DIR/got-z80.z80" | head -20
	fi
fi

# ── 12: error handling — missing input must fail loudly, not silently succeed ──
# No -b/-h: the documented default is "search .hex first, then .bin", and the
# error must name both candidates. A silent rc=0 here would be a false pass.
( cd "$WORK_DIR" && "$D52_BIN" no-such-input >"$WORK_DIR/missing.log" 2>&1 )
rc=$?
if [ "$rc" -ne 0 ] && grep -q "Can't open either" "$WORK_DIR/missing.log" \
	&& grep -q "no-such-input.hex" "$WORK_DIR/missing.log" \
	&& grep -q "no-such-input.bin" "$WORK_DIR/missing.log"; then
	ok "d52 reports missing input (rc=$rc, \"Can't open either '...hex' nor '...bin'\")"
else
	bad "d52 missing-input handling (rc=$rc)"
fi

# ── 13: d48 real disassembly (same Intel HEX input, own binary and output) ──
rm -f "$RUN_DIR/bench0.d48"
( cd "$RUN_DIR" && "$D48_BIN" bench0 >"$WORK_DIR/d48-run.log" 2>&1 )
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$RUN_DIR/bench0.d48" ] \
	&& grep -q "D48 V3.4.1" "$RUN_DIR/bench0.d48" \
	&& grep -q "end" "$RUN_DIR/bench0.d48"; then
	ok "d48 disassembles bench0.hex: $(wc -l <"$RUN_DIR/bench0.d48") lines written to bench0.d48"
else
	bad "d48 disassembly (rc=$rc)"
fi

# ── 14: -u upper-case output mode ──
rm -f "$RUN_DIR/bench0.d52"
( cd "$RUN_DIR" && "$D52_BIN" -zADuC84x.cyc -u bench0 >"$WORK_DIR/d52-upper.log" 2>&1 )
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$RUN_DIR/bench0.d52" ] \
	&& grep -q "PUSH" "$RUN_DIR/bench0.d52" \
	&& ! grep -q "push" "$RUN_DIR/bench0.d52"; then
	ok "d52 -u emits upper-case mnemonics (PUSH present, push absent)"
else
	bad "d52 -u upper-case mode (rc=$rc)"
fi

# ── 15: -t trace/analyze mode (code/data analysis + control file generation) ──
TRACE_DIR="$WORK_DIR/trace"
rm -rf "$TRACE_DIR"
mkdir -p "$TRACE_DIR"
cp "$DATA_DIR/bench0.hex" "$TRACE_DIR/bench0.hex"
( cd "$TRACE_DIR" && "$D52_BIN" -t bench0 >"$WORK_DIR/d52-trace.log" 2>&1 )
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$TRACE_DIR/bench0.ctl" ] && [ -s "$TRACE_DIR/bench0.d52" ] \
	&& grep -q "Generated by D52 V3.4.1" "$TRACE_DIR/bench0.ctl" \
	&& grep -q "c 0000-003a" "$TRACE_DIR/bench0.ctl"; then
	ok "d52 -t trace/analyze wrote bench0.ctl (code space 0000-003a) and a disassembly"
else
	bad "d52 -t trace/analyze mode (rc=$rc)"
fi

echo "TOTAL: $((PASS + FAIL))  PASS: $PASS  FAIL: $FAIL"
if [ "$FAIL" -ne 0 ]; then
	echo "RESULT: FAIL"
	exit 1
fi
echo "RESULT: ALL PASS (d52 test_package: 15 assertions, incl. 8 upstream golden replays)"
