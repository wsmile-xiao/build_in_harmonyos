#!/bin/sh
# test_tclconfig.sh — formal consumer regression test for tclConfig.sh.
#
# Sources the packaged lib/tclConfig.sh exactly like a Tcl extension consumer
# (Expect configure presets TCL_BIN_DIR before sourcing) and asserts:
#   A4: tclConfig.sh exists in the package
#   A5: tclConfig.sh contains no .conan2/p/b/ build-machine or '//' paths
#   A6: TCL_SRC_DIR is set after sourcing
#   A7: ${TCL_SRC_DIR}/generic/tclInt.h is reachable
#   A8: TCL_INCLUDE_SPEC usable
#   A9: TCL_LIB_SPEC usable
#   A10: TCL_BUILD_LIB_SPEC usable
set -u

if [ $# -ne 1 ]; then
    echo "[FAIL] usage: test_tclconfig.sh <package_folder>"
    exit 1
fi
pkg_dir="$1"
tclconfig="$pkg_dir/lib/tclConfig.sh"

# A4
if [ ! -f "$tclconfig" ]; then
    echo "[FAIL] $tclconfig missing"
    exit 1
fi
echo "[PASS] tclConfig.sh exists: $tclconfig"

# A5
if grep -qE '\.conan2/p/b/|/build-release/|//include|//lib|//bin' "$tclconfig"; then
    echo "[FAIL] tclConfig.sh contains build-machine or '//' paths"
    exit 1
fi
echo "[PASS] tclConfig.sh has no .conan2/p/b/ or '//' paths"

# Source with TCL_BIN_DIR preset (Expect configure behaviour, L2649 -> L2662)
TCL_BIN_DIR="$pkg_dir/lib"
. "$tclconfig"

# A6
if [ -z "${TCL_SRC_DIR:-}" ]; then
    echo "[FAIL] TCL_SRC_DIR empty after sourcing"
    exit 1
fi
echo "[PASS] TCL_SRC_DIR set: $TCL_SRC_DIR"

# A7
if [ -f "${TCL_SRC_DIR}/generic/tclInt.h" ]; then
    echo "[PASS] \${TCL_SRC_DIR}/generic/tclInt.h reachable"
else
    echo "[FAIL] \${TCL_SRC_DIR}/generic/tclInt.h not reachable: ${TCL_SRC_DIR}/generic/tclInt.h"
    exit 1
fi

# A8-A10
for spec in TCL_INCLUDE_SPEC TCL_LIB_SPEC TCL_BUILD_LIB_SPEC; do
    eval "value=\${$spec:-}"
    if [ -z "$value" ]; then
        echo "[FAIL] $spec empty after sourcing"
        exit 1
    fi
    case "$value" in
        *'/'*) : ;;
        *) echo "[FAIL] $spec unusable: $value"; exit 1 ;;
    esac
    echo "[PASS] $spec = $value"
done

echo "=== tclConfig.sh consumer checks OK (7 assertions) ==="
exit 0
