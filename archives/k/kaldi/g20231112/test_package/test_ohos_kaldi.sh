#!/usr/bin/env bash
# test_package/test_ohos_kaldi.sh
#
# 鸿蒙特有测试：验证 kaldi/g20231112 的产物确实是 HarmonyOS(aarch64, musl) 原生构建，
# 且在本机真机上可加载可运行。
#
# 用法: test_ohos_kaldi.sh <kaldi_package_folder> <bindir>
set -euo pipefail

PKG="${1:?kaldi package folder}"
BIN="${2:?bindir}"

TMPD="${TMPDIR:-$HOME/tmp}/kaldi-ohos-test.$$"
mkdir -p "$TMPD"
trap 'rm -rf "$TMPD"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "  ok - $*"; }

echo "[ohos-test 1/5] 平台必须是 HarmonyOS aarch64"
[ "$(uname -m)" = "aarch64" ] || fail "uname -m = $(uname -m)，期望 aarch64"
[ "$(uname)" = "HarmonyOS" ] || fail "uname = $(uname)，期望 HarmonyOS"
ok "uname = HarmonyOS, arch = aarch64"

echo "[ohos-test 2/5] 全部 kaldi 静态库为非空 ar 归档"
count=0
for a in "$PKG"/lib/libkaldi-*.a; do
  [ -f "$a" ] || fail "缺少静态库: $a"
  head -c8 "$a" | grep -q '!<arch>' || fail "$(basename "$a") 不是 ar 归档"
  [ "$(stat -c%s "$a")" -gt 1000 ] || fail "$(basename "$a") 体积异常"
  count=$((count+1))
done
[ "$count" -eq 21 ] || fail "kaldi 静态库数量 = $count，期望 21"
ok "21 个 libkaldi-*.a 均为有效 ar 归档"

echo "[ohos-test 3/5] 静态库成员为 aarch64 ELF 对象"
for a in "$PKG"/lib/libkaldi-base.a "$PKG"/lib/libkaldi-matrix.a "$PKG"/lib/libkaldi-online2.a; do
  member=$(ar t "$a" | head -n1)
  ar p "$a" "$member" > "$TMPD/member.o"
  machine=$(readelf -h "$TMPD/member.o" | grep -o 'AArch64' || true)
  [ "$machine" = "AArch64" ] || fail "$(basename "$a"):$member 非 AArch64 ELF"
done
ok "静态库成员为 AArch64 ELF"

echo "[ohos-test 4/5] 公共头文件齐全"
for h in base/kaldi-common.h matrix/kaldi-matrix.h matrix/sp-matrix.h \
         fstext/fstext-lib.h lat/kaldi-lattice.h online2/online-nnet3-decoding.h; do
  [ -f "$PKG/include/$h" ] || fail "缺少头文件 $h"
done
ok "公共头文件齐全"

echo "[ohos-test 5/5] 消费者共享库可在真机 dlopen（musl 加载器）"
SO="$BIN/libkaldi_ohos_probe.so"
[ -f "$SO" ] || fail "缺少 $SO"
readelf -h "$SO" | grep -q 'AArch64' || fail "探针 .so 非 AArch64"
cat > "$TMPD/dl.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char **argv) {
  void *h = dlopen(argv[1], RTLD_NOW);
  if (!h) { printf("dlopen failed: %s\n", dlerror()); return 1; }
  int (*f)(void) = (int (*)(void))dlsym(h, "kaldi_ohos_probe");
  if (!f) { printf("dlsym failed: %s\n", dlerror()); return 2; }
  int v = f();
  printf("kaldi_ohos_probe() = %d\n", v);
  return v == 8 ? 0 : 3;
}
EOF
cxx="${CONFIG_CXX:-/data/service/hnp/bin/clang}"
"$cxx" -o "$TMPD/dl" "$TMPD/dl.c" -ldl
LD_LIBRARY_PATH="$(dirname "$SO")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$TMPD/dl" "$SO"
ok "dlopen + 调用成功（kaldi 静态库已正确链入共享库并可在 OHOS 加载）"

echo "OHOS-SPECIFIC TEST PASSED"
