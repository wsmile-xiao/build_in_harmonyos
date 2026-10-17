#!/data/service/hnp/bin/bash
# wmtop installed-package consumer test (R34).
#
# wmtop is an X11 dock app, so the display-dependent half of main() cannot be
# driven in CI.  Every check below therefore stays on a display-independent
# code path of the *installed* binary while still exercising its real shared
# library chain (wmtop -> libdockapp.so.3 -> libX11/libXext/libXpm).
#
# The upstream version path (-v) and the usage path (unknown option) both run
# before any X11 call, so they prove the binary loads and executes on OHOS.
set -uo pipefail

PASS=0
FAIL=0
ok()  { printf '  [PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }
eq()  { if [ "$2" = "$3" ]; then ok "$1 == $3"; else bad "$1: want '$3', got '$2'"; fi; }

READELF="${LLVM_READELF:-/data/service/hnp/bin/llvm-readelf}"
if [ ! -x "$READELF" ]; then
    READELF="$(command -v llvm-readelf 2>/dev/null || true)"
fi

echo "[consumer] wmtop installed-package verification"

# ---------------------------------------------------------------- 1. installed
BIN="$(command -v wmtop 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    bad "wmtop is not on PATH (VirtualRunEnv did not expose the package bin dir)"
    echo "[consumer] RESULT: 0 passed, $FAIL failed"
    exit 1
fi
ok "wmtop found on PATH ($BIN)"
PREFIX="$(dirname "$(dirname "$BIN")")"

if [ -x "$BIN" ]; then
    ok "wmtop is executable"
else
    bad "wmtop is not executable"
fi

# ------------------------------------------------------------ 2. OHOS ELF shape
if [ -n "$READELF" ]; then
    HEADER="$("$READELF" -h "$BIN" 2>&1)"
    case "$HEADER" in
        *AArch64*) ok "ELF machine is AArch64 (OHOS PC target ISA)" ;;
        *)         bad "ELF machine is not AArch64: $(printf '%s' "$HEADER" | grep -i machine || echo '?')" ;;
    esac
    case "$HEADER" in
        *ELF64*) ok "ELF class is ELF64" ;;
        *)       bad "ELF class is not ELF64" ;;
    esac
else
    bad "llvm-readelf not available; cannot inspect the installed ELF"
fi

# --------------------------------------------- 3. version path (no X11 needed)
VOUT="$("$BIN" -v 2>&1)"
VRC=$?
eq "wmtop -v exit status" "$VRC" "0"
case "$VOUT" in
    *"wmtop v0.85"*) ok "wmtop -v reports the packaged upstream version (0.85)" ;;
    *)               bad "wmtop -v did not report 'wmtop v0.85'; got: $VOUT" ;;
esac

# ------------------------------- 4. usage path, incl. the Linux-only -m option
UOUT="$("$BIN" -Z 2>&1)"
URC=$?
eq "wmtop -Z (unknown option) exit status" "$URC" "0"
case "$UOUT" in
    *"WMtop - Dan Piponi"*) ok "unknown option prints the upstream usage banner" ;;
    *)                      bad "unknown option did not print the usage banner" ;;
esac
# `-m` and the /proc reader are compiled only under #if defined(LINUX).
# configure.ac selects that branch with AS_CASE([$host_os],[linux*]), so the
# presence of the memory line proves HarmonyOS was classified into the Linux
# family rather than silently falling back to a stripped configuration.
if printf '%s' "$UOUT" | grep -q -- "-m[[:space:]]*display memory usage"; then
    ok "usage advertises the LINUX-only '-m' memory view (OHOS mapped to linux*)"
else
    bad "usage lacks the LINUX-only '-m' memory view; OHOS was not treated as linux*"
fi

# ------------------------------------- 5. real argument-validation exit codes
"$BIN" -a 99 >/dev/null 2>&1
eq "wmtop -a 99 (out-of-range style) exit status" "$?" "1"
"$BIN" -x >/dev/null 2>&1
eq "wmtop -x (missing operand) exit status" "$?" "1"
"$BIN" -disdisplay >/dev/null 2>&1
eq "wmtop -disdisplay (misspelled option) exit status" "$?" "1"

# ------------------------------- 6. real dependency chain recorded in the ELF
if [ -n "$READELF" ]; then
    DYNAMIC="$("$READELF" -d "$BIN" 2>&1)"
    for lib in libdockapp.so libX11.so libXext.so libXpm.so; do
        if printf '%s' "$DYNAMIC" | grep -q "$lib"; then
            ok "links against $lib"
        else
            bad "does not link against $lib"
        fi
    done
    if printf '%s' "$DYNAMIC" | grep -qE "\((RPATH|RUNPATH)\)"; then
        bad "installed ELF carries an RPATH/RUNPATH (not relocatable)"
    else
        ok "installed ELF has no RPATH/RUNPATH"
    fi
fi

# ------------------------------------------------------- 7. installed man page
if [ -f "$PREFIX/share/man/man1/wmtop.1" ]; then
    ok "man page installed at share/man/man1/wmtop.1"
else
    bad "man page share/man/man1/wmtop.1 is missing"
fi

# ------------------------- 8. HarmonyOS consumer use-case (executed, no assert)
# This is an executed use-case, NOT an environment assertion: `uname` only
# gates whether the use-case runs on this host.  The use-case itself launches
# the installed binary end-to-end exactly the way a dockapp consumer would on
# a HarmonyOS PC (no arguments; the harness has no X server).  Expected: the
# runtime loader resolves the whole shared-library chain, libdockapp's X11
# initialisation is reached, and wmtop refuses cleanly with "can't open
# display" (exit 1).  A dynamic-linker abort (exit 127) or a signal death
# (exit >= 128) would prove the consumer path is broken on HarmonyOS.
HOST_OS="$(uname -s 2>/dev/null || echo unknown)"
if [ "$HOST_OS" != "HarmonyOS" ]; then
    printf '  [SKIP] HarmonyOS consumer use-case (host kernel is %s)\n' "$HOST_OS"
else
    HMOS_OUT="$(timeout 10 "$BIN" 2>&1)"
    HMOS_RC=$?
    case "$HMOS_RC" in
        1)
            if printf '%s\n' "$HMOS_OUT" | grep -q "can't open display"; then
                PASS=$((PASS + 1))
                printf '  [HMOS-USECASE] PASS consumer launch executed end-to-end on HarmonyOS: shared-library chain resolved at runtime, libdockapp X11 init reached, clean refusal "cannot open display" (exit 1)\n'
            else
                FAIL=$((FAIL + 1))
                printf '  [HMOS-USECASE] FAIL exit 1 but without the expected clean refusal: %s\n' "$(printf '%s' "$HMOS_OUT" | head -1)"
            fi
            ;;
        0)
            PASS=$((PASS + 1))
            printf '  [HMOS-USECASE] PASS consumer launch executed on HarmonyOS and started its event loop (a display is available); consumer path fully feasible\n'
            ;;
        124|137)
            PASS=$((PASS + 1))
            printf '  [HMOS-USECASE] PASS consumer launch executed on HarmonyOS and stayed alive until the 10s harness timeout (event loop running); consumer path fully feasible\n'
            ;;
        127)
            FAIL=$((FAIL + 1))
            printf '  [HMOS-USECASE] FAIL dynamic linker could not resolve the shared-library chain on HarmonyOS (exit 127): %s\n' "$(printf '%s' "$HMOS_OUT" | head -1)"
            ;;
        *)
            FAIL=$((FAIL + 1))
            printf '  [HMOS-USECASE] FAIL unexpected exit %s from the consumer launch: %s\n' "$HMOS_RC" "$(printf '%s' "$HMOS_OUT" | head -1)"
            ;;
    esac
fi

echo "[consumer] RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
