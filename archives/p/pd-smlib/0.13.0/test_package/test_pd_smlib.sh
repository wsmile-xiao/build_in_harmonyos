#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-smlib 0.13.0.
#
# The package installs Pd external shared objects (*.pd_linux) that are
# loaded by Pd at patch-load time, so the test drives the real OHOS `pd`
# binary (from the puredata package) against the installed externals and
# checks the DSP->control results printed by the SMLib classes.
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_smlib.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_smlib.pd}"

EXPECTED_EXTERNALS=40

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/vmax.pd_linux" ] || { echo "FAIL: vmax.pd_linux missing"; exit 1; }

# --- OHOS specific check 1: every installed external is an aarch64 ELF object.
# e_machine lives at offset 18 (little endian); EM_AARCH64 == 0xb7.
bad_arch=0
for so in "$EXT_DIR"/*.pd_linux; do
    machine="$(od -An -tx1 -j18 -N2 "$so" | tr -d ' \n')"
    if [ "$machine" != "b700" ]; then
        echo "FAIL: not an aarch64 ELF: $so (e_machine=$machine)"
        bad_arch=1
    fi
done
if [ "$bad_arch" -eq 0 ]; then
    echo "PASS: all installed SMLib externals are aarch64 ELF shared objects"
else
    exit 1
fi

# --- OHOS specific check 2: the complete upstream class set is installed.
n_ext="$(find "$EXT_DIR" -name '*.pd_linux' | wc -l | tr -d ' ')"
if [ "$n_ext" -ne "$EXPECTED_EXTERNALS" ]; then
    echo "FAIL: expected $EXPECTED_EXTERNALS externals, found $n_ext"
    exit 1
fi
echo "PASS: $n_ext SMLib externals installed"

# --- local emulation only: the WSL/qemu guest libc predates the glibc fortify
# shims that Pd references (__fd_chk).  Preload the prepared shim for the pd
# process when it exists; on a native OHOS runner (CI) the path is absent and
# pd is invoked directly.
FDCHK_SHIM=/opt/ohos-guest/lib/libfdchkshim.so
run_pd() {
    if [ -f "$FDCHK_SHIM" ]; then
        LD_PRELOAD="$FDCHK_SHIM" "$@"
    else
        "$@"
    fi
}

WORK="${TMPDIR:-.}/pd-smlib-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

LOG="$WORK/pd.log"
if command -v timeout >/dev/null 2>&1; then
    run_pd timeout 25 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
else
    run_pd "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
fi

echo "--- pd output ---"
cat "$LOG"
echo "--- end pd output ---"

fails=0
check() {
    if grep -q "$1" "$LOG"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2 (expected '$1')"
        fails=$((fails + 1))
    fi
}

check "SMLIB_VMAX: 9"          "SMLib [vmax 3 9 4] -> 9"
check "SMLIB_VMIN: 3"          "SMLib [vmin 3 9 4] -> 3"
check "SMLIB_VSUM: 10"         "SMLib [vsum 1 2 3 4] -> 10"
check "SMLIB_VMTOF: 440"       "SMLib [vmtof 69] -> 440 Hz"
check "SMLIB_VFTOM: 69"        "SMLib [vftom 440] -> 69 MIDI"
check "SMLIB_VCLIP: 0 5 10"    "SMLib [vclip 0 10] of -5 5 50 -> 0 5 10"
check "SMLIB_VVPLUS: 11 22 33" "SMLib [vvplus 10 20 30] + 1 2 3 -> 11 22 33"
check "SMLIB_VRMS: 3.53553"    "SMLib [vrms 3 4] -> 3.53553"
check "SMLIB_VSTD: 2"          "SMLib [vstd 2 4 4 4 5 5 7 9] -> 2"
check "SMLIB_VABS: 1 2.5 3"    "SMLib [vabs -1 -2.5 3] -> 1 2.5 3"
check "SMLIB_VMTOF_LIST: 261.626 523.251 1046.5" "SMLib [vmtof 60 72 84] -> 261.626 523.251 1046.5"
check "SMLIB_VCOG: 2.33333"    "SMLib [vcog 1 2 3] -> 2.33333"
check "SMLIB_VDBTORMS: 0"      "SMLib [vdbtorms 0] -> 0"
check "SMLIB_VNMAX: 9"         "SMLib [vnmax 1 9 5] -> 9"
check "SMLIB_VNMAX_IDX: 2"     "SMLib [vnmax 1 9 5] -> index 2"

echo "SMLIB_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
