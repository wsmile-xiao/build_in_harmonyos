#!/bin/bash
# test_zarith.sh — Verify ZArith library is installed and functional
# Usage: sh test_zarith.sh <zarith_package_folder>
# Called by test_package/conanfile.py test() method (env=conanbuild, ocaml toolchain in PATH)
set -euo pipefail

# 临时目录：mktemp -d 保证可移植性与并发安全，trap 退出时清理
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/zarith_test.XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

ZARITH_PKG="${1:-}"
if [ -n "$ZARITH_PKG" ]; then
    ZARITH_DIR="$ZARITH_PKG/lib/ocaml/zarith"
else
    ZARITH_DIR=$(find /storage/Users/currentUser/.conan2/p -maxdepth 9 -path "*zarith*/p/lib/ocaml/zarith" -type d 2>/dev/null | head -1)
fi

# 1. Verify zarith library files exist
if [ -z "$ZARITH_DIR" ] || [ ! -f "$ZARITH_DIR/zarith.cma" ]; then
    echo "ERROR: zarith.cma not found (dir=$ZARITH_DIR)" >&2
    exit 1
fi
echo "zarith library found: $ZARITH_DIR"

# 2. ocaml toolchain from PATH (conanbuild env injects tool_requires bin)
OCAML_BIN="$(command -v ocamlrun || true)"
OCAMLC_BIN="$(command -v ocamlc || true)"
if [ -z "$OCAML_BIN" ] || [ -z "$OCAMLC_BIN" ]; then
    echo "ERROR: ocaml toolchain (ocamlrun/ocamlc) not in PATH" >&2
    echo "PATH=$PATH" >&2
    exit 1
fi

# 3. Verify big integer arithmetic: 42 + 1 = 43 (bytecode via ocamlrun)
echo "Running big integer addition test (42 + 1 = 43)..."
echo 'print_endline (string_of_int (Z.to_int (Z.add (Z.of_int 42) (Z.of_int 1))))' > "$TMP_DIR/zarith_test.ml"
# 字节码运行需要 C stubs 动态库（dllzarith.so），设置 CAML_LD_LIBRARY_PATH 指向 stublibs
STUBLIB="$(dirname "$ZARITH_DIR")/stublibs"
export CAML_LD_LIBRARY_PATH="$STUBLIB"
"$OCAMLC_BIN" -I "$ZARITH_DIR" -linkall -o "$TMP_DIR/zarith_test.byte" "$ZARITH_DIR/zarith.cma" "$TMP_DIR/zarith_test.ml" 2>&1 \
  && RESULT=$("$OCAML_BIN" "$TMP_DIR/zarith_test.byte") \
  || { echo "ERROR: ocamlc/ocamlrun failed" >&2; exit 1; }
echo "42+1 = $RESULT"
if [ "$RESULT" = "43" ]; then
    echo "All tests passed."
else
    echo "ERROR: expected 43, got $RESULT" >&2
    exit 1
fi
