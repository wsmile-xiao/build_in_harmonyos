#!/bin/sh
# test_protocols.sh <package_folder>
#
# Consumer-side validation of the plasma-wayland-protocols data package.
# Locates the native PlasmaWaylandProtocolsConfig.cmake shipped in the package,
# resolves PLASMA_WAYLAND_PROTOCOLS_DIR by evaluating that config with
# `cmake -P`, then validates every protocol XML and asserts the resolved
# directory really lives inside the package.  Prints a machine-readable tally
# `assertions=N failures=0` and exits non-zero on any failure.
set -eu
# Any remaining pipeline must not hide the failing stage's status (a `find`
# error would otherwise be swallowed by whatever it is piped into).
set -o pipefail

PKG="${1:?usage: test_protocols.sh <package_folder>}"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# `-print -quit` rather than `find … | head -1`: the pipeline form lets `head`
# close the pipe early and discards find's exit status (e.g. an unreadable
# directory under $PKG), which made a broken search look like "config missing";
# with `set -o pipefail` that same pipeline would instead abort the run before
# the `assertions=` tally is printed.  The substitution is guarded so a find
# failure still reports a tally.
CONFIG=""
if ! CONFIG=$(find "$PKG" -name PlasmaWaylandProtocolsConfig.cmake -print -quit 2>/dev/null); then
    echo "FAIL: find failed while locating PlasmaWaylandProtocolsConfig.cmake under $PKG"
    echo "assertions=1 failures=1"
    exit 1
fi
if [ -z "$CONFIG" ]; then
    echo "FAIL: PlasmaWaylandProtocolsConfig.cmake not found under $PKG"
    echo "assertions=1 failures=1"
    exit 1
fi
echo "[info] native CMake package config: $CONFIG"

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/pwp_resolve.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT
OUT="$WORKDIR/pwp_dir.txt"

cmake -DPWP_CONFIG="$CONFIG" -DPWP_OUT="$OUT" -P "$HERE/resolve_pwp_dir.cmake"

PWP_DIR=""
# Not `[ -f "$OUT" ] && PWP_DIR=$(cat "$OUT")`: under `set -e` a failing test
# would terminate the script before the tally is printed.
if [ -f "$OUT" ]; then
    PWP_DIR=$(cat "$OUT")
fi
if [ -z "$PWP_DIR" ]; then
    echo "FAIL: could not resolve PLASMA_WAYLAND_PROTOCOLS_DIR from $CONFIG"
    echo "assertions=1 failures=1"
    exit 1
fi
if [ ! -d "$PWP_DIR" ]; then
    echo "FAIL: PLASMA_WAYLAND_PROTOCOLS_DIR does not exist: $PWP_DIR"
    echo "assertions=1 failures=1"
    exit 1
fi
echo "[info] PLASMA_WAYLAND_PROTOCOLS_DIR=$PWP_DIR"

# The package root is handed to the validator so that the containment check is
# part of the same tally/exit code instead of a separate ad-hoc test here.
python3 "$HERE/validate_protocols.py" "$PWP_DIR" "$PKG"
