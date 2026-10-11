#!/bin/bash
# test_package/test.sh -- xml-light 2.5 consumer test (L0c test source)
# R34: really consumes the tested package:
#   1. asserts the 8 packaged artifacts exist (cma/cmxa/cmxs/a + 3 module
#      cmi + META);
#   2. bytecode-compiles test_xml_light.ml against the packaged
#      xml_light.cma (registry OCaml 4.14.1 has no findlib, so explicit
#      archive linkage is the standard form; compile-only);
#   3. native-compiles (xml_light.cmxa) + runs it: exercises Xml
#      (parse_string / attrib / children / to_string round-trip), Dtd
#      (parse / check / prove) with positive and negative controls, and
#      asserts "ALL TESTS PASSED" in the output;
#   4. HarmonyOS e2e consumer case: real-file DTD-validated parsing on the
#      OHOS filesystem, asserts "ALL OHOS E2E PASSED".
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
for a in xml_light.cma xml_light.cmxa xml_light.cmxs xml_light.a \
         xml.cmi dtd.cmi xmlParser.cmi META; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (8/8)"

echo "=== bytecode compile (compile-only, explicit cma linkage) ==="
ocamlc -I "$LIB_DIR" "$LIB_DIR/xml_light.cma" -o /dev/null test_xml_light.ml
echo "bytecode compile: OK"

echo "=== native compile + run (Xml + Dtd, positive & negative controls) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/xml_light.cmxa" \
         -o test_xml_light.exe test_xml_light.ml
OUT="$(./test_xml_light.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (file I/O -> parse -> DTD prove) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/xml_light.cmxa" \
         -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
