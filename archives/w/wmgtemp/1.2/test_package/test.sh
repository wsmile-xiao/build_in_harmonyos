#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS (OHOS) consumer test for wmgtemp.
#
# Runs inside the conanrun env (PATH includes the installed bin/ and
# LD_LIBRARY_PATH contains every conan dependency libdir).
#
# wmgtemp is an X11 dockapp that requires:
#   - libsensors (lm_sensors) for sensor data
#   - libdockapp (and transitively libX11, libXpm, libXext)
#
# The test verifies:
#   1. The binary exists and is executable
#   2. `wmgtemp -h` prints the help banner and exits 0
#   3. `wmgtemp -h` prints the version string "wmgtemp v1.2"
#   4. Without DISPLAY, the binary either fails at sensors_init
#      (no sensors on OHOS) or reaches XOpenDisplay — in either case
#      the ELF and full shared-library closure load and relocate natively
#      on OHOS (no "Error loading shared library" loader errors).
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

report() { # name rc
    TOTAL=$((TOTAL + 1))
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        echo "PASS [PASS] $1"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL [FAIL] $1"
    fi
}

BIN="$(command -v wmgtemp)"
if [ -z "$BIN" ]; then
    echo "FAIL wmgtemp not found in PATH"
    echo "[debug] PATH=$PATH"
    exit 1
fi
echo "[debug] BIN=$BIN"
echo "[debug] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"

# ------------------------------------------------------------------
# Fallback staging: copy the dependency closure into the app sandbox
# and point LD_LIBRARY_PATH there (consumer flow on OHOS devices whose
# conan cache sits on a loader-inaccessible mount).
# ------------------------------------------------------------------
stage_libs() {
    local run_dir="${TMPDIR:-$HOME/tmp}/wmgtemp-test-$$-libs"
    mkdir -p "$run_dir" 2>/dev/null || run_dir="$HOME/tmp/wmgtemp-test-$$-libs"
    mkdir -p "$run_dir" || return 1
    echo "$LD_LIBRARY_PATH" | tr ':' '\n' | while read -r d; do
        [ -n "$d" ] && [ -d "$d" ] && cp -L "$d"/*.so* "$run_dir/" 2>/dev/null
    done
    export LD_LIBRARY_PATH="$run_dir"
}

loader_blocked() { # output -> rc
    case "$1" in
        *"Error loading shared library"*|*"Error relocating"*) return 0 ;;
        *) return 1 ;;
    esac
}

# ------------------------------------------------------------------
# HarmonyOS consumer case 1: help output (consumes the installed binary).
# `wmgtemp -h` calls display_usage() which prints the help banner and
# exits 0 (unlike wmmisc which exits 1).
# ------------------------------------------------------------------
echo "[test 1] wmgtemp -h (OHOS consumer CLI feasibility)"
OUT="$("$BIN" -h 2>&1)"
RC=$?
if loader_blocked "$OUT"; then
    stage_libs
    OUT="$("$BIN" -h 2>&1)"
    RC=$?
fi
case "$OUT" in
    *"Usage: wmgtemp"*) : ;;
    *) RC=2 ;;
esac
if [ "$RC" -eq 0 ]; then
    report "wmgtemp -h prints Usage and exits 0" 0
else
    echo "[debug] case1 rc=$RC out=[${OUT:-<empty>}]"
    report "wmgtemp -h prints Usage and exits 0" 1
fi

# ------------------------------------------------------------------
# HarmonyOS consumer case 2: version string.
# display_usage() prints "wmgtemp v<PACKAGE_VERSION>" — verify it's "v1.2".
# ------------------------------------------------------------------
echo "[test 2] wmgtemp -h version string"
case "$OUT" in
    *"wmgtemp v1.2"*) : ;;
    *) RC=3 ;;
esac
if [ "$RC" -eq 0 ]; then
    report "wmgtemp -h prints version v1.2" 0
else
    echo "[debug] case2 rc=$RC out=[${OUT:-<empty>}]"
    report "wmgtemp -h prints version v1.2" 1
fi

# ------------------------------------------------------------------
# HarmonyOS consumer case 3: runtime linkage feasibility.
# Without DISPLAY, wmgtemp either:
#   a) fails at sensors_init (no /sys/class/hwmon on OHOS), or
#   b) reaches XOpenDisplay() and fails with "can't open display".
# Both outcomes prove the ELF + libsensors + libdockapp/X11 closure
# load and relocate natively on OHOS. Only a loader error (missing
# shared library) is a failure.
# ------------------------------------------------------------------
echo "[test 3] wmgtemp without DISPLAY (OHOS consumer runtime feasibility)"
# Use unset + explicit assignment instead of `env -u` (system env has
# broken OpenSSL symbols on OHOS)
SAVED_DISPLAY="${DISPLAY:-}"
unset DISPLAY
OUT2="$("$BIN" 2>&1)"
RC2=$?
DISPLAY="$SAVED_DISPLAY"
if loader_blocked "$OUT2"; then
    stage_libs
    unset DISPLAY
    OUT2="$("$BIN" 2>&1)"
    RC2=$?
    DISPLAY="$SAVED_DISPLAY"
fi
if loader_blocked "$OUT2"; then
    echo "[debug] case3 loader blocked: rc=$RC2 out=[${OUT2:-<empty>}]"
    report "wmgtemp loads full shared-lib closure on OHOS" 1
else
    report "wmgtemp loads full shared-lib closure on OHOS" 0
fi

echo "----------------------------------------"
echo "total=$TOTAL passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
