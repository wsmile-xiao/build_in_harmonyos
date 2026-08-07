#!/bin/sh
# run_pagodacf_tests.sh — pagodacf 0.1 Conan test_package shell harness
#
# Why this file exists:
#   CI L0c (ci/conan/build_and_test.sh:245) only recognises test sources
#   ending in .c/.cpp/.cc/.cxx/.sh/.py. pagodacf's real test source is
#   t_pagodacf.ml (OCaml), which L0c cannot see → `no_test_sources` gate
#   failure (E230). This wrapper carries an L0c-accepted suffix AND
#   substantively exercises the pagodacf (Cf) library: it compiles and
#   runs t_pagodacf.ml against the installed cf.cma, exactly mirroring
#   what test_package/conanfile.py::test() does, so it is a real test
#   source, not a gate marker (R34/E230 forbid_1).
#
#   The actual CI/HMBS test execution path is Conan's test() method in
#   test_package/conanfile.py, which also produces the HMBS JSON evidence
#   markers. This script is the L0c-satisfying surface for the same test
#   and can be run standalone for local verification; it does NOT emit
#   HMBS markers (avoid double-source with conanfile.py).
#
# Usage:
#   ./run_pagodacf_tests.sh [<cf_libdir>] [<ocaml_pkg>]
#     <cf_libdir>  directory containing cf.cma + dllcf.so (default: probe)
#     <ocaml_pkg>  ocaml/4.14.1 Conan package folder (default: probe)
#   Exit status: 0 = all TAP tests passed, non-zero = compile/run failure
#                 or any `not ok` line seen.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/t_pagodacf.ml"
OUT="${TMPDIR:-/tmp}/t_pagodacf.$$"
trap 'rm -f "$OUT" "$OUT.bc.log" 2>/dev/null || true' EXIT INT TERM

cf_libdir="${1:-}"
ocaml_pkg="${2:-}"

# Probe cf_libdir: look for cf.cma under typical Conan layout.
if [ -z "$cf_libdir" ]; then
    for cand in \
        "$SCRIPT_DIR/../../package/lib/cf" \
        "$SCRIPT_DIR/../package/lib/cf" \
        "$(pwd)/package/lib/cf"; do
        if [ -f "$cand/cf.cma" ]; then
            cf_libdir="$cand"
            break
        fi
    done
fi
if [ -z "$cf_libdir" ] || [ ! -f "$cf_libdir/cf.cma" ]; then
    echo "[fail] cf.cma not found; pass <cf_libdir> as \$1" >&2
    exit 2
fi

# Probe ocaml_pkg: look for ocamlc under typical Conan cache layout.
if [ -z "$ocaml_pkg" ]; then
    if command -v ocamlc >/dev/null 2>&1; then
        ocaml_bin="$(dirname "$(command -v ocamlc)")"
        ocaml_pkg="$(dirname "$ocaml_bin")"
    else
        for cand in \
            "$SCRIPT_DIR/../../../../ocaml/4.14.1/package" \
            "$SCRIPT_DIR/../../../ocaml/4.14.1/package"; do
            if [ -x "$cand/bin/ocamlc" ]; then
                ocaml_pkg="$cand"
                break
            fi
        done
    fi
fi
if [ -z "$ocaml_pkg" ] || [ ! -x "$ocaml_pkg/bin/ocamlc" ]; then
    echo "[fail] ocamlc not found; pass <ocaml_pkg> as \$2" >&2
    exit 2
fi

ocaml_bin="$ocaml_pkg/bin"
ocaml_lib="$ocaml_pkg/lib/ocaml"
ocaml_stubs="$ocaml_lib/stublibs"

# Environment mirroring test_package/conanfile.py::generate() (R17/R21/R22):
#   PATH          — ocamlc/ocamlrun resolution
#   OCAMLLIB      — stdlib.cmi location (R10: Unbound module Stdlib)
#   CAML_LD_LIBRARY_PATH — bytecode loader finds dllcf.so/dllunix.so
#   LD_PRELOAD    — OHOS loader registers unix_error before dllcf.so RTLD_NOW
PATH="$ocaml_bin:$PATH"
export PATH OCAMLLIB
OCAMLLIB="$ocaml_lib"
CAML_LD_LIBRARY_PATH="$ocaml_stubs:$ocaml_bin:$cf_libdir"
export CAML_LD_LIBRARY_PATH
LD_PRELOAD="$ocaml_stubs/dllunix.so"
export LD_PRELOAD

echo "[step] Compiling t_pagodacf.ml against cf.cma..."
ocamlc -I "$cf_libdir" -I +unix -o "$OUT" unix.cma cf.cma "$SRC"

echo "[step] Running bytecode test..."
ocamlrun "$OUT" > "$OUT.bc.log" 2>&1 || { rc=$?; cat "$OUT.bc.log" >&2; exit "$rc"; }

# Parse TAP output (mirrors conanfile.py TAP tally).
discovered=0
executed=0
passed=0
failed=0
while IFS= read -r line; do
    case "$line" in
        1..*) discovered="${line#1..}" ;;
        ok\ *) executed=$((executed + 1)); passed=$((passed + 1)) ;;
        "not ok "*) executed=$((executed + 1)); failed=$((failed + 1)) ;;
    esac
done < "$OUT.bc.log"

echo "[result] discovered=$discovered executed=$executed passed=$passed failed=$failed"
if [ "$failed" -gt 0 ] || [ "$executed" -eq 0 ]; then
    echo "[fail] t_pagodacf.ml did not pass cleanly" >&2
    exit 1
fi
echo "[ok] all $passed t_pagodacf.ml sub-tests passed"
