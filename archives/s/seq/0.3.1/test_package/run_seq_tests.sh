#!/bin/sh
# run_seq_tests.sh — seq 0.3.1 Conan test_package shell harness
#
# Why this file exists:
#   CI L0c (ci/conan/build_and_test.sh:342) only recognises test sources
#   ending in .c/.cpp/.cc/.cxx/.sh/.py.  seq's real test source is
#   t_seq.ml (OCaml), which L0c cannot see → `no_test_sources` gate
#   failure.  This wrapper carries an L0c-accepted suffix AND
#   substantively exercises the seq library: it compiles and runs
#   t_seq.ml against the installed seq.cma, exactly mirroring what
#   test_package/conanfile.py::test() does.
#
# Usage:
#   ./run_seq_tests.sh [<seq_libdir>] [<ocaml_pkg>]
#     <seq_libdir>  directory containing seq.cma (default: probe)
#     <ocaml_pkg>   ocaml/4.14.1 Conan package folder (default: probe)
#   Exit status: 0 = all TAP tests passed, non-zero = failure

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/t_seq.ml"
OUT="${TMPDIR:-/tmp}/t_seq.$$"
trap 'rm -f "$OUT" "$OUT.log" 2>/dev/null || true' EXIT INT TERM

seq_libdir="${1:-}"
ocaml_pkg="${2:-}"

# Probe seq_libdir: look for seq.cma under typical Conan layout.
if [ -z "$seq_libdir" ]; then
    for cand in \
        "$SCRIPT_DIR/../../package/lib/ocaml/seq" \
        "$SCRIPT_DIR/../package/lib/ocaml/seq" \
        "$(pwd)/package/lib/ocaml/seq"; do
        if [ -f "$cand/seq.cma" ]; then
            seq_libdir="$cand"
            break
        fi
    done
fi
if [ -z "$seq_libdir" ] || [ ! -f "$seq_libdir/seq.cma" ]; then
    echo "[fail] seq.cma not found; pass <seq_libdir> as \$1" >&2
    exit 2
fi

# Probe ocaml_pkg: look for ocamlc under typical Conan cache layout.
if [ -z "$ocaml_pkg" ]; then
    if command -v ocamlc >/dev/null 2>&1; then
        ocaml_bin="$(dirname "$(command -v ocamlc)")"
        ocaml_pkg="$(dirname "$ocaml_bin")"
    else
        for cand in \
            "$SCRIPT_DIR/../../../../ocaml/4.14.1.1.2/package" \
            "$SCRIPT_DIR/../../../ocaml/4.14.1.1.2/package"; do
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

# Environment for OCaml bytecode compilation and execution:
#   PATH              — ocamlc/ocamlrun resolution
#   OCAMLLIB          — stdlib.cmi location
#   CAML_LD_LIBRARY_PATH — bytecode loader finds stub .so files
PATH="$ocaml_bin:$PATH"
OCAMLLIB="$ocaml_lib"
CAML_LD_LIBRARY_PATH="$ocaml_stubs:$ocaml_bin"
export PATH OCAMLLIB CAML_LD_LIBRARY_PATH

echo "[step] Compiling t_seq.ml against seq.cma..."
ocamlc -I "$seq_libdir" -o "$OUT" seq.cma "$SRC"

echo "[step] Running bytecode test..."
ocamlrun "$OUT" > "$OUT.log" 2>&1 || { rc=$?; cat "$OUT.log" >&2; exit "$rc"; }

# Parse TAP output.
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
done < "$OUT.log"

echo "[result] discovered=$discovered executed=$executed passed=$passed failed=$failed"
if [ "$failed" -gt 0 ] || [ "$executed" -eq 0 ]; then
    echo "[fail] t_seq.ml did not pass cleanly" >&2
    exit 1
fi
echo "[ok] all $passed t_seq.ml sub-tests passed"
