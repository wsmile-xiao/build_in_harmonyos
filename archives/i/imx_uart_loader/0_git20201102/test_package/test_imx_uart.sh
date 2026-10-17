#!/bin/sh
# imx_uart_loader consumer test.
#
# imx_uart is a hardware-facing serial loader: a full functional test needs an
# i.MX SoC in serial boot mode on a real UART, which no runner has. What CAN be
# asserted on the target, and is asserted here, is that the installed binary
# really executes on this platform and that its command-line surface behaves as
# observed on the device.
#
# Every invocation is wrapped in `timeout`. That is not decoration: bare
# `imx_uart` with NO arguments HANGS indefinitely on this platform (see the
# note below), and an unguarded call would wedge the whole verify run rather
# than fail it. A first revision of this script did exactly that.
#
# Observed behaviour on the Harmony PC (aarch64/OHOS, clang 15):
#
#   imx_uart              -> HANGS (no output, never exits)   <- not exercised
#   imx_uart -h           -> exit 0, usage banner
#   imx_uart --help       -> exit 0, usage banner
#   imx_uart -V           -> exit 0, version banner
#   imx_uart --bogus-opt  -> exit 0, "unrecognized option" + usage banner
#
# Note the exit codes: -h/--help/-V and even an unrecognised option all exit 0,
# because parse_opts() returns >0 and main() maps that to EXIT_SUCCESS.
set -u

BIN="${1:-imx_uart}"
failures=0
checked=0

# `timeout` is present on the device (it is how the hang below was measured),
# but do not silently drop the guard if it ever is not.
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT="timeout 15"
else
    echo "FAIL: 'timeout' is unavailable; refusing to run unguarded probes" >&2
    exit 1
fi

# check <desc> <expected-exit> <needle> [args...]
check() {
    desc="$1"; want_rc="$2"; needle="$3"; shift 3
    checked=$((checked + 1))

    out=$($TIMEOUT "$BIN" "$@" 2>&1)
    rc=$?

    if [ "$rc" -eq 124 ]; then
        echo "FAIL: $desc — HUNG (killed by timeout)"
        failures=$((failures + 1))
        return
    fi
    if [ "$rc" -ne "$want_rc" ]; then
        echo "FAIL: $desc — expected exit $want_rc, got $rc"
        failures=$((failures + 1))
        return
    fi
    case "$out" in
        *"$needle"*)
            echo "ok: $desc (exit $rc)"
            ;;
        *)
            echo "FAIL: $desc — expected to see '$needle', got:"
            echo "$out" | head -4
            failures=$((failures + 1))
            ;;
    esac
}

# The binary must actually run and expose its documented CLI surface.
check "help flag"         0 "Usage: imx_uart"           -h
check "long help flag"    0 "Usage: imx_uart"           --help
check "version flag"      0 "0.2pre"                    -V
check "invalid option"    0 "unrecognized option"       --definitely-not-an-option

if [ "$failures" -ne 0 ]; then
    echo "test_imx_uart: $failures of $checked check(s) failed"
    exit 1
fi

echo "test_imx_uart: all $checked checks passed"
exit 0
