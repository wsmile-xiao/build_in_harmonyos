#!/bin/sh
# test_package/test.sh — topkg 1.1.1 consumer test (L0c test source)
# POSIX sh on purpose: conan test() invokes it via `sh`. Failures are
# accumulated (no `set -e`) so every check is counted; the script exits
# non-zero at the end if any check failed.
# Usage: test.sh <pkg_dir> <ocaml_lib> <ocaml_bin> <cc> <shim>
set -u

PKG_DIR="${1:?}"; OCAML_LIB="${2:?}"; OCAML_BIN="${3:?}"; CC="${4:?}"; SHIM="${5:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$SHIM:$OCAML_BIN:$PATH"

cd "$(dirname "$0")"
LIB_DIR="$PKG_DIR/lib/ocaml/topkg"
ASSERT=0; FAIL=0
chk() {
    ASSERT=$((ASSERT + 1))
    if [ "$2" != "0" ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL: $1"
    fi
}
run_last() {  # run_last <cmd...> -> OUT = full output, RC = command rc
    OUT="$("$@" 2>&1)"; RC=$?
}

echo "[step] artifact presence"
for a in topkg.cma topkg.cmxa topkg.cmxs topkg.a topkg.cmi META topkg.mli; do
    [ -f "$LIB_DIR/$a" ]; chk "artifact $a" $?
done

echo "[step] native consumer compile + run"
ocamlopt -I "$LIB_DIR" -cc "$CC" "$LIB_DIR/topkg.cmxa" test_topkg.ml -o test_topkg.exe
chk "native compile" $?
run_last ./test_topkg.exe
chk "native run, rc=$RC" $RC
printf '%s\n' "$OUT"
case "$OUT" in *"ALL TESTS PASSED"*) RC=0 ;; *) RC=1 ;; esac
chk "native output" $RC

echo "[step] bytecode consumer compile + run (ocamlrun)"
ocamlc -I "$LIB_DIR" "$LIB_DIR/topkg.cma" test_topkg.ml -o test_topkg.byte
chk "bytecode compile" $?
run_last ocamlrun ./test_topkg.byte
chk "bytecode run, rc=$RC" $RC
printf '%s\n' "$OUT"
case "$OUT" in *"ALL TESTS PASSED"*) RC=0 ;; *) RC=1 ;; esac
chk "bytecode output" $RC

echo "shell_assertions=$ASSERT failures=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    echo "test_package: topkg consumer tests FAILED" >&2
    exit 1
fi
echo "ALL TESTS PASSED"
