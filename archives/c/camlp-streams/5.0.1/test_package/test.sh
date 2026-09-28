#!/bin/bash
# test_package/test.sh -- camlp-streams 5.0.1 consumer test (L0c test source)
# R34: really consumes the tested package:
#   1. asserts the 7 packaged artifacts exist (cma/cmxa/cmxs/a + cmi + META);
#   2. bytecode-compiles test_camlp_streams.ml against the packaged
#      camlp_streams.cma (registry OCaml 4.14.1 has no findlib, so explicit
#      archive linkage is the standard form; compile-only);
#   3. native-compiles (camlp_streams.cmxa) + runs it: exercises Stream
#      (of_list/next) and Genlex (make_lexer) end-to-end, asserts
#      "ALL TESTS PASSED" in the output.
set -eu

LIB_DIR="${1:?usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin>}"
OCAML_LIB="${2:?}"
OCAML_BIN="${3:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$OCAML_BIN:$PATH"
export OCAMLPATH="$(dirname "$(dirname "$LIB_DIR")")"

cd "$(dirname "$0")"

echo "=== artifact presence check ==="
for a in camlp_streams.cma camlp_streams.cmxa camlp_streams.cmxs \
         camlp_streams.a stream.cmi genlex.cmi META; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (7/7)"

echo "=== bytecode compile (compile-only, explicit cma linkage) ==="
ocamlc -I "$LIB_DIR" "$LIB_DIR/camlp_streams.cma" -o /dev/null test_camlp_streams.ml
echo "bytecode compile: OK"

echo "=== native compile + run (exercises Stream + Genlex) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/camlp_streams.cmxa" \
         -o test_camlp_streams.exe test_camlp_streams.ml
OUT="$(./test_camlp_streams.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (rule12: file I/O -> Stream.of_channel -> Genlex) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/camlp_streams.cmxa" \
         -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
