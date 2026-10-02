#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS (OHOS) consumer test for proftmb 1.1.12.
#
# Runs inside the conanrun env (PATH includes the installed bin/, and the
# package libdir is exposed through both conanrun LD_LIBRARY_PATH and the
# binary's own RUNPATH $ORIGIN/../lib).
#
# Upstream proftmb 1.1.12 has no automated test suite (Makefile.am declares no
# check target and no check_PROGRAMS). The cases below are HarmonyOS consumer
# cases added by this adaptation (named end-to-end runs, rule12) — they execute
# the installed binary the way a real OHOS consumer would.
#
# OHOS notes (verified on-device 2026-09-30):
#   * The installed binary is self-signed in package() with binary-sign-tool
#     (E077): the OHOS toolchain embeds a stale empty .codesign section that
#     must be stripped with objcopy before signing, and the signed output loses
#     the exec bit (restored via chmod).
#   * OHOS musl loader does not follow symlinks when resolving DT_NEEDED
#     (E050): package() flattens libgsl.so.28 / libgslcblas.so.0 into
#     <pkg>/lib as entity files, and the binary's RUNPATH is $ORIGIN/../lib.
#   * The upstream options file hardcodes -d "//share/proftmb"; a real
#     consumer overrides it with -d <datadir> AFTER the @options file.
set -u

PASS=0
FAIL=0
TOTAL=0

report() { # name rc
    TOTAL=$((TOTAL + 1))
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        echo "[PASS] $1"
    else
        FAIL=$((FAIL + 1))
        echo "[FAIL] $1"
    fi
}

BIN="$(command -v proftmb)"
if [ -z "$BIN" ]; then
    echo "FAIL: proftmb not found in PATH"
    echo "[debug] PATH=$PATH"
    exit 1
fi
echo "[debug] BIN=$BIN"
echo "[debug] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"

PKG_ROOT="$(dirname "$(dirname "$BIN")")"
DATADIR="$PKG_ROOT/share/proftmb"
EXAMPLES="$PKG_ROOT/share/doc/proftmb/examples"

if [ ! -f "$DATADIR/options" ] || [ ! -f "$EXAMPLES/example.Q" ]; then
    echo "FAIL: packaged data incomplete: datadir=$DATADIR examples=$EXAMPLES"
    exit 1
fi

# Writable scratch dir for prediction outputs (HMDFS: el2 cache is writable)
OUTDIR="$(mktemp -d 2>/dev/null)"
if [ -z "$OUTDIR" ] || [ ! -d "$OUTDIR" ]; then
    OUTDIR="${TMPDIR:-/data/storage/el2/base/cache}/proftmb-hc.$$"
    mkdir -p "$OUTDIR" || { echo "FAIL: cannot create scratch dir"; exit 1; }
fi

# ----------------------------------------------------------------------
# HarmonyOS consumer case 1 (HC-1): CLI invocation feasibility.
# Executes the installed, self-signed ELF end to end and asserts the
# upstream version banner. Proves exec permission + musl loader + full
# shared-library closure (libgsl.so.28 / libgslcblas.so.0 / libc++_shared)
# work natively on OHOS.
# ----------------------------------------------------------------------
echo "[HC-1] proftmb --version (OHOS consumer CLI feasibility)"
OUT1="$("$BIN" --version 2>&1)"
RC1=$?
echo "$OUT1" | grep -q "proftmb 1.1.12" && RC1=0 || RC1=2
report "HC-1: proftmb --version prints upstream banner (exec+loader closure)" "$RC1"

# ----------------------------------------------------------------------
# HarmonyOS consumer case 2 (HC-2): full prediction pipeline.
# Feeds the upstream example PSSM (example.Q) through the complete
# HMM pipeline: @options loads -s Swiss8.arch / -t Swiss8.params /
# -a StateRedux4 / -b ReduxDecode4 / -z Swiss_Zcurve / -x ZCalibration /
# -n bact.comp; -d overrides the options file's hardcoded //share/proftmb.
# Asserts the upstream success message on stdout.
# ----------------------------------------------------------------------
echo "[HC-2] proftmb @options -d <datadir> -q example.Q (full prediction run)"
OUT2="$("$BIN" @"$DATADIR/options" -d "$DATADIR" -q "$EXAMPLES/example.Q" -o "$OUTDIR/hc2" 2>&1)"
RC2=$?
echo "[debug] HC-2 stdout: $OUT2"
case "$OUT2" in
    *"Successfully finished Prediction"*) : ;;
    *) RC2=2 ;;
esac
report "HC-2: full prediction on example.Q finishes successfully" "$RC2"

# ----------------------------------------------------------------------
# HarmonyOS consumer case 3 (HC-3): output correctness.
# The prediction must reproduce the upstream reference outputs shipped in
# share/doc/proftmb/examples byte for byte (tabular + per-residue .dat).
# ----------------------------------------------------------------------
echo "[HC-3] prediction output vs upstream reference (byte-for-byte)"
RC3=0
for pair in "hc2_proftmb_tabular.txt:example_proftmb_tabular.txt" \
            "hc2_dat.txt:example_dat.txt"; do
    got="${pair%%:*}"
    want="${pair##*:}"
    if [ ! -f "$OUTDIR/$got" ]; then
        echo "[debug] missing output file: $OUTDIR/$got"
        RC3=2
        break
    fi
    if ! cmp -s "$OUTDIR/$got" "$EXAMPLES/$want"; then
        echo "[debug] diff mismatch: $got vs $want"
        RC3=3
    fi
done
report "HC-3: prediction output matches upstream reference outputs" "$RC3"

rm -rf "$OUTDIR" 2>/dev/null

echo "----------------------------------------"
echo "total=$TOTAL passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
