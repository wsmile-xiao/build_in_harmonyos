#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS (OHOS) consumer test for wmmisc.
#
# Runs inside the conanrun env (PATH includes the installed bin/ and
# LD_LIBRARY_PATH contains every conan dependency libdir).
#
# OHOS notes (verified on-device 2026-09-27):
#   * The OHOS dynamic loader can only open shared libraries on local
#     filesystems; caches mounted on network/HDFS filesystems are not
#     loader-readable.  Direct execution is therefore tried first and a
#     sandbox-local staging of the dependency closure is used as fallback
#     (that staging is exactly what a real OHOS consumer does).
#   * Upstream quirk: wmmisc prints usage/version and exits with status 1
#     (exit(1) after dockapp_show_help in src/dockapp_main.c).
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

report() { # name rc
    TOTAL=$((TOTAL + 1))
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        echo "✅ [PASS] $1"
    else
        FAIL=$((FAIL + 1))
        echo "❌ [FAIL] $1"
    fi
}

BIN="$(command -v wmmisc)"
if [ -z "$BIN" ]; then
    echo "❌ wmmisc not found in PATH"
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
    local run_dir="${TMPDIR:-$HOME/tmp}/wmmisc-test-$$-libs"
    mkdir -p "$run_dir" 2>/dev/null || run_dir="$HOME/tmp/wmmisc-test-$$-libs"
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
# HarmonyOS consumer case 1: CLI help output (consumes the installed binary).
# Asserts the Usage banner and the upstream exit(1) quirk.
# ------------------------------------------------------------------
echo "[test 1] wmmisc -h (OHOS consumer CLI feasibility)"
OUT="$("$BIN" -h 2>&1)"
RC=$?
if loader_blocked "$OUT"; then
    stage_libs
    OUT="$("$BIN" -h 2>&1)"
    RC=$?
fi
case "$OUT" in
    Usage:*) : ;;
    *) RC=2 ;;
esac
if [ "$RC" -eq 1 ]; then
    report "wmmisc -h prints Usage and exits 1 (upstream quirk)" 0
else
    echo "[debug] case1 rc=$RC out=[${OUT:-<empty>}]"
    report "wmmisc -h prints Usage and exits 1 (upstream quirk)" 1
fi

# ------------------------------------------------------------------
# HarmonyOS consumer case 2: runtime linkage feasibility.
# Without DISPLAY the program must fail gracefully at XOpenDisplay
# ("can't open display", exit 1).  Reaching that point proves the ELF,
# musl libc and the complete libdockapp/X11 shared-library closure load
# and relocate natively on OHOS.
# ------------------------------------------------------------------
echo "[test 2] wmmisc without DISPLAY (OHOS consumer runtime feasibility)"
OUT2="$(env -u DISPLAY "$BIN" 2>&1)"
RC2=$?
if loader_blocked "$OUT2"; then
    stage_libs
    OUT2="$(env -u DISPLAY "$BIN" 2>&1)"
    RC2=$?
fi
case "$OUT2" in
    *"can't open display"*) : ;;
    *) RC2=3 ;;
esac
if [ "$RC2" -eq 1 ]; then
    report "wmmisc loads full shared-lib closure on OHOS and fails gracefully without DISPLAY" 0
else
    echo "[debug] case2 rc=$RC2 out=[${OUT2:-<empty>}]"
    report "wmmisc loads full shared-lib closure on OHOS and fails gracefully without DISPLAY" 1
fi

echo "----------------------------------------"
echo "total=$TOTAL passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
