#!/bin/sh
# test_package/test.sh — xmlm 1.4.0 consumer test (L0c test source)
# POSIX sh on purpose: the conan test() invokes it via `sh` (CI worker has no
# guaranteed bash); pipefail is therefore not used.
# R34: really consumes the tested package:
#   1. asserts the 8 packaged artifacts exist (cma/cmxa/cmxs/a/cmi/ml/mli/META);
#   2. bytecode compile (ocamlc + xmlm.cma) and run via ocamlrun;
#   3. native compile (ocamlopt + xmlm.cmxa) and run on the device;
#   4. HarmonyOS e2e consumer case with real file I/O (test_ohos_e2e.ml);
#   5. packaged xmltrip tool smoke run.
# Usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin> <bin_dir> <cc>
set -eu

LIB_DIR="${1:?usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin> <bin_dir> <cc>}"
OCAML_LIB="${2:?}"
OCAML_BIN="${3:?}"
BIN_DIR="${4:?}"
CC="${5:?}"

# OHOS has no GNU `as`; ocamlopt's baked assembler is a bare `as`. Provide a
# shim forwarding to the OHOS clang from conan conf (same mechanism as the
# recipe build()).
SHIM_DIR="$(pwd)/.test-toolchain"
mkdir -p "$SHIM_DIR"
printf '#!/bin/sh\nexec %s -c "$@"\n' "$CC" > "$SHIM_DIR/as"
chmod +x "$SHIM_DIR/as"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$SHIM_DIR:$OCAML_BIN:$PATH"

cd "$(dirname "$0")"

echo "=== artifact presence check ==="
for a in xmlm.cma xmlm.cmxa xmlm.cmxs xmlm.a xmlm.cmi xmlm.ml xmlm.mli META; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
if [ ! -x "$BIN_DIR/xmltrip" ]; then
    echo "ERROR: package missing executable: $BIN_DIR/xmltrip" >&2
    exit 1
fi
echo "artifacts: OK (8/8 + bin/xmltrip)"

echo "=== bytecode compile + run (explicit xmlm.cma linkage) ==="
ocamlc -I "$LIB_DIR" "$LIB_DIR/xmlm.cma" test_xmlm.ml -o test_xmlm.byte
ocamlrun ./test_xmlm.byte

echo "=== native compile + run (explicit xmlm.cmxa linkage) ==="
ocamlopt -I "$LIB_DIR" -cc "$CC" "$LIB_DIR/xmlm.cmxa" test_xmlm.ml -o test_xmlm.exe
OUT="$(./test_xmlm.exe)"
printf '%s\n' "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (file I/O -> Channel -> re-encode) ==="
ocamlopt -I "$LIB_DIR" -I "$OCAML_LIB" -cc "$CC" "$LIB_DIR/xmlm.cmxa" "$OCAML_LIB/unix.cmxa" \
         test_ohos_e2e.ml -o test_ohos_e2e.exe
E2E_OUT="$(./test_ohos_e2e.exe)"
printf '%s\n' "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== packaged xmltrip smoke (parse-only) ==="
printf '<a b="c">t</a>\n' > xmltrip_sample.xml
"$BIN_DIR/xmltrip" -p xmltrip_sample.xml
rm -f xmltrip_sample.xml
echo "xmltrip: OK"

echo "=== All tests passed ==="
