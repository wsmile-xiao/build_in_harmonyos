#!/bin/sh
# OCaml 4.14.4 test_package — 验证编译器工具链版本 + native 功能
# OHOS hmmac 拒绝直执行 shebang 脚本，须由 conanfile.py 用显式解释器调用（/bin/sh test.sh）
# bin 目录由 conanfile.py 显式传入（$1），不依赖 PATH，无硬编码本机路径

# 不使用 set -e：本脚本通过 fail 变量显式聚合各检查结果，
# set -e 在函数返回非零时行为因 shell 实现而异（POSIX 未定义），不可移植。
set -u

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin directory not provided or not found"
    exit 1
fi

fail=0

check_version() {
    tool="$1"
    if [ -x "$BIN_DIR/$tool" ]; then
        "$BIN_DIR/$tool" -version >/dev/null 2>&1 || fail=1
    else
        echo "FAIL: $tool not found in $BIN_DIR"
        fail=1
    fi
}

check_version ocaml
check_version ocamlc
check_version ocamlopt

# native 功能测试：用 ocamlopt 编译并运行 hello.ml，
# 验证 native 编译器 + 运行时全链路（非仅版本检查）
hello_ml="${2:-}"
if [ -z "$hello_ml" ] || [ ! -f "$hello_ml" ]; then
    echo "FAIL: hello.ml source not provided or not found"
    fail=1
else
    # 优先 mktemp；失败则退回当前目录（conan test 运行时 cwd 可写）。
    # 不依赖 /tmp（OHOS /tmp 为只读 erofs）
    workdir="$(mktemp -d 2>/dev/null || echo "./ocaml-test.$$")"
    if [ ! -d "$workdir" ]; then
        mkdir -p "$workdir"
    fi
    if "$BIN_DIR/ocamlopt" "$hello_ml" -o "$workdir/hello" >/dev/null 2>&1; then
        out="$("$workdir/hello" 2>&1)"
        if [ "$out" = "hello, OCaml 4.14.4 on HarmonyOS PC" ]; then
            echo "PASS: ocamlopt compiled and ran hello.ml"
        else
            echo "FAIL: hello.ml ran but output mismatch: $out"
            fail=1
        fi
    else
        echo "FAIL: ocamlopt could not compile hello.ml"
        fail=1
    fi
    rm -rf "$workdir"
fi

if [ "$fail" -ne 0 ]; then
    echo "test.sh: OCaml toolchain smoke test FAILED"
    exit 1
fi

echo "test.sh: OCaml toolchain smoke test OK"
exit 0

