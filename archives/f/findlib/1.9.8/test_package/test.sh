#!/bin/sh
# findlib (ocamlfind) 1.9.8 smoke test — consumer view.
#
# Verifies that the installed `ocamlfind` can:
#   1. report its version
#   2. list and query packages from the OCaml site-lib
#   3. actually drive ocamlopt to compile+link a program that uses a package
#
# OHOS hmmac refuses direct execution of shebang scripts, so this script is
# invoked by conanfile.py with an explicit interpreter (/bin/sh test.sh).
# Arguments are passed explicitly to avoid PATH guessing / hard-coded paths.

# Not using `set -e`: the script aggregates results via the `fail` variable
# and `set -e` behaviour on non-zero function returns is shell-dependent.
set -u

FINDLIB_BIN="${1:-}"
OCAML_BIN="${2:-}"
OCAML_STDLIB="${3:-}"

if [ -z "$FINDLIB_BIN" ] || [ ! -d "$FINDLIB_BIN" ]; then
    echo "FAIL: findlib bin directory not provided or not found"
    exit 1
fi
if [ -z "$OCAML_BIN" ] || [ ! -d "$OCAML_BIN" ]; then
    echo "FAIL: ocaml bin directory not provided or not found"
    exit 1
fi

OCAMLFIND="$FINDLIB_BIN/ocamlfind"
if [ ! -x "$OCAMLFIND" ]; then
    echo "FAIL: ocamlfind not found in $FINDLIB_BIN"
    exit 1
fi

export PATH="$OCAML_BIN:$FINDLIB_BIN:$PATH"
# The OCaml tools and ocamlfind need to locate the standard library; the path
# embedded at build time may be stale, so it is passed explicitly here.
if [ -n "$OCAML_STDLIB" ] && [ -d "$OCAML_STDLIB" ]; then
    OCAMLLIB="$OCAML_STDLIB"
    export OCAMLLIB
    if [ -d "$OCAML_STDLIB/stublibs" ]; then
        CAML_LD_LIBRARY_PATH="$OCAML_STDLIB/stublibs"
        export CAML_LD_LIBRARY_PATH
    fi
fi

fail=0

# 1. package listing + query (ocamlfind has no bare -version flag; the version
#    is reported by `list` and the install location by `query`)
"$OCAMLFIND" list 2>/dev/null | grep -q '^findlib ' || {
    echo "FAIL: ocamlfind list does not report the findlib package"
    fail=1
}
"$OCAMLFIND" query findlib >/dev/null 2>&1 || {
    echo "FAIL: ocamlfind query findlib failed"
    fail=1
}

# 2. drive the compiler: build a program that links the standard library,
#    then run it and check the output.
workdir="$(mktemp -d "${TMPDIR:-.}/findlib-test.XXXXXX")" || {
    echo "FAIL: cannot create temporary directory"
    exit 1
}
trap 'rm -rf "$workdir"' EXIT

cat >"$workdir/hello.ml" <<'EOF'
let () = print_string "findlib_e2e_ok\n"
EOF

# 原生编译：OHOS 上 OCaml `-custom` 字节码混合产物无法独立运行（平台限制），
# 使用 ocamlopt 原生路径完成同等语义的编译+链接验证。
if ! "$OCAMLFIND" ocamlopt -linkpkg -package unix -o "$workdir/hello" \
        "$workdir/hello.ml" >"$workdir/build.log" 2>&1; then
    echo "FAIL: ocamlfind could not build the test program"
    grep -v WARNING "$workdir/build.log" | head -5
    fail=1
elif [ "$("$workdir/hello" 2>&1)" != "findlib_e2e_ok" ]; then
    echo "FAIL: test program produced unexpected output"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "test.sh: findlib smoke test FAILED"
    exit 1
fi

echo "test.sh: findlib smoke test OK"
exit 0
