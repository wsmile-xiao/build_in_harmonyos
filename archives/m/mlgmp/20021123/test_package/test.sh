#!/bin/sh
# mlgmp test_package — 用 ocamlopt/ocamlc 编译并运行 Gmp 模块调用程序
#
# 参数: $1 = test.ml 路径
#       其余参数为 "KEY=value" 环境变量（OCAMLLIB/PATH/CAML_LD_LIBRARY_PATH/MLGMP_DIR）
#
# OHOS 说明:
#   - /tmp 只读，工作目录用 $TMPDIR 或当前目录
#   - 字节码程序经 ocamlrun 显式运行（-custom ELF 无法直接执行）
set -euo pipefail

test_ml="${1:-}"
shift

# 注入环境变量
for kv in "$@"; do
    case "$kv" in
        *=*) export "$kv" ;;
    esac
done

if [ -z "$test_ml" ] || [ ! -f "$test_ml" ]; then
    echo "FAIL: test.ml not found"
    exit 1
fi

if [ -z "${MLGMP_DIR:-}" ]; then
    echo "FAIL: MLGMP_DIR not set"
    exit 1
fi

fail=0
workdir="${TMPDIR:-.}/mlgmp-test.$$"
rm -rf "$workdir" && mkdir -p "$workdir" || { echo "FAIL: cannot mkdir $workdir"; exit 1; }

# --- native 路径: ocamlopt + gmp.cmxa ---
if ocamlopt -I "$MLGMP_DIR" "$MLGMP_DIR/gmp.cmxa" "$test_ml" -o "$workdir/test_opt" 2>"$workdir/opt.err"; then
    if "$workdir/test_opt" >"$workdir/opt.out" 2>&1; then
        echo "PASS: native (ocamlopt + gmp.cmxa)"
    else
        echo "FAIL: native test_opt run failed"
        cat "$workdir/opt.out"
        fail=1
    fi
else
    echo "FAIL: ocamlopt compile failed"
    cat "$workdir/opt.err"
    fail=1
fi

# --- bytecode 路径: ocamlc + gmp.cma + dllmlgmp.so ---
if ocamlc -dllib dllmlgmp.so -I "$MLGMP_DIR" "$MLGMP_DIR/gmp.cma" "$test_ml" -o "$workdir/test_bc" 2>"$workdir/bc.err"; then
    if CAML_LD_LIBRARY_PATH="$MLGMP_DIR:${CAML_LD_LIBRARY_PATH:-}" \
            ocamlrun "$workdir/test_bc" >"$workdir/bc.out" 2>&1; then
        echo "PASS: bytecode (ocamlc + gmp.cma + ocamlrun)"
    else
        echo "FAIL: bytecode test_bc run failed"
        cat "$workdir/bc.out"
        fail=1
    fi
else
    echo "FAIL: ocamlc compile failed"
    cat "$workdir/bc.err"
    fail=1
fi

rm -rf "$workdir"

if [ "$fail" -ne 0 ]; then
    echo "test_package: mlgmp smoke test FAILED"
    exit 1
fi
echo "test_package: mlgmp smoke test OK"
exit 0
