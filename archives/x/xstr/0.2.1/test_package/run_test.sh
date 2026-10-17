#!/usr/bin/env sh
# xstr 0.2.1 test_package 驱动脚本
#
# 用 OCaml 工具链（ocamlc/ocamlrun）编译并运行消费者测试 test.ml，
# 真实调用 xstr 库三个模块（Xstr_search/Xstr_split/Xstr_match）的 API 并断言
# 已知结果（R34：非空壳测试）。conanfile.py 的 build()/test() 通过本脚本
# 驱动测试，保证 CI L0c 认可的 .sh 测试源真实参与执行。
#
# 用法: run_test.sh <ocaml-bin-dir> <ocaml-lib-dir> <stublibs-dir> \
#                   <xstr-lib-dir> <test.ml> <输出二进制> <结果文件>
set -eu

OCAML_BIN="$1"
OCAML_LIB="$2"
STUBLIBS="$3"
XSTR_DIR="$4"
TEST_SRC="$5"
OUT="$6"
RES="$7"

# OCAMLLIB 显式指向 ocaml 包 stdlib，否则 ocamlc 报 `Unbound module Stdlib`
# （ocaml 包编译期嵌入的 --prefix 在缓存目录会失效）。
export PATH="$OCAML_BIN:$PATH"
export OCAMLLIB="$OCAML_LIB"
# ocamlrun 加载 dllunix.so 等 C stub 依赖 stublibs
export CAML_LD_LIBRARY_PATH="$STUBLIBS"

# 编译消费者程序并运行，输出重定向到结果文件（test() 读回解析断言计数）。
"$OCAML_BIN/ocamlc" -I "$XSTR_DIR" "$XSTR_DIR/xstr.cma" "$TEST_SRC" -o "$OUT"
"$OCAML_BIN/ocamlrun" "$OUT" > "$RES" 2>&1
