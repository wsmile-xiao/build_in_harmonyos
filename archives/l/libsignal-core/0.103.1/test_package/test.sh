#!/bin/sh
# libsignal-core 0.103.1 consumer probe — 用 rustc 直链打包的 rlib 闭包。
# 用法: sh test.sh <libdir>
# HMBS 注入 SHELL=/bin/sh、CONFIG_SHELL=/bin/sh（平台诊断 shell_getcwd），
# 本脚本按 POSIX sh 编写。
set -u

LIBDIR="$1"
HERE=$(dirname "$0")

emit_failed() {
  echo "HMBS_TEST_PACKAGE_RESULT={\"status\":\"failed\",\"framework\":\"rustc-probe\",\"command\":\"rustc --extern libsignal_core=<pkg>/lib/liblibsignal_core.rlib\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":1,\"skipped\":0}"
}

RUSTC=$(command -v rustc 2>/dev/null || true)
if [ -z "$RUSTC" ] || [ ! -x "$RUSTC" ]; then
  echo "SKIP: rustc not on PATH (toolchain bootstrap failed?)"
  echo "HMBS_TEST_PACKAGE_RESULT={\"status\":\"skipped\",\"framework\":\"rustc-probe\",\"command\":\"rustc --extern libsignal_core\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":1}"
  exit 0
fi

CORE_RLIB="$LIBDIR/liblibsignal_core.rlib"
# 依赖 rlib 为哈希后缀名（librand-<hash>.rlib），glob 解析
RAND_RLIB=$(ls "$LIBDIR"/librand-*.rlib 2>/dev/null | head -n 1 || true)
# proc-macro crate 以哈希后缀 .so 交付（元数据在 .so 内，消费者全图
# 元数据加载必需，真机第 7 轮实证缺 libzerocopy_derive-*.so 必挂）
PM_SO=$(ls "$LIBDIR"/libzerocopy_derive-*.so 2>/dev/null | head -n 1 || true)
if [ ! -f "$CORE_RLIB" ] || [ -z "$RAND_RLIB" ] || [ -z "$PM_SO" ]; then
  echo "FAIL: rlib closure incomplete under $LIBDIR"
  ls "$LIBDIR" 2>/dev/null || true
  emit_failed
  exit 1
fi

# 裸 rustc 不读 RUSTFLAGS（那是 cargo 的变量），链接器必须显式传 -C
# linker；test_package/conanfile.py 的 _build_env() 已把 CC 解析为 clang
# （OHOS 无 cc 符号，真机第 8 轮实证 rustc 回退调用 cc 报 EACCES）
CC_LINKER="${CC:-clang}"
if ! "$RUSTC" --edition 2024 "$HERE/probe.rs" \
     --extern "libsignal_core=$CORE_RLIB" \
     --extern "rand=$RAND_RLIB" \
     -C "linker=$CC_LINKER" \
     -L "dependency=$LIBDIR" -o probe 2>probe-compile.log; then
  echo "FAIL: probe.rs compile error:"
  cat probe-compile.log
  emit_failed
  exit 1
fi

OUT=$(./probe) && RC=0 || RC=1
echo "$OUT"
ASSERTS=$(echo "$OUT" | grep -o 'PROBE_ASSERTS=[0-9]*' | head -n 1 | cut -d= -f2)
FAILS=$(echo "$OUT" | grep -o 'FAILS=[0-9]*' | head -n 1 | cut -d= -f2)
ASSERTS=${ASSERTS:-0}
FAILS=${FAILS:-1}
PASSED=$((ASSERTS - FAILS))
if [ "$RC" -eq 0 ] && [ "$FAILS" -eq 0 ] && [ "$ASSERTS" -gt 0 ]; then
  echo "HMBS_TEST_PACKAGE_RESULT={\"status\":\"passed\",\"framework\":\"rustc-probe\",\"command\":\"rustc --extern libsignal_core=<pkg>/lib/liblibsignal_core.rlib\",\"discovered\":$ASSERTS,\"executed\":$ASSERTS,\"passed\":$PASSED,\"failed\":0,\"skipped\":0}"
  exit 0
fi
emit_failed
exit 1
