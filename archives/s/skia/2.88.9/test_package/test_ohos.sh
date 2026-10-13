#!/bin/sh
# test_package/test_ohos.sh — 鸿蒙平台特有校验（与消费者用例分开计数，不重复计入）
#
# OHOS 平台特性：
#   T1 产物必须是 AArch64 ELF
#   T2 产物必须带 .codesign 段（OHOS 用户存储执行 ELF 的必要条件；strip 会使其失效）
#   T3 必须是 musl 动态链接（OHOS 无 glibc loader）
#   T4 运行期 tmp 目录约定（/tmp 为只读 erofs，需依赖可写 TMPDIR）
set -u

BIN="${PKG_BIN:-./consumer}"
if [ ! -x "$BIN" ]; then
  BIN="$(find . -maxdepth 3 -name consumer -type f 2>/dev/null | head -1)"
fi

fails=0
checks=0
c() { checks=$((checks + 1)); if eval "$2"; then echo "PASS $checks: $1"; else echo "FAIL $checks: $1"; fails=$((fails + 1)); fi; }

echo "--- skia 2.88.9 HarmonyOS-specific checks ---"

c "T1 consumer is AArch64 ELF" "readelf -h \"$BIN\" 2>/dev/null | grep -q 'AArch64'"
c "T2 .codesign section present" "readelf -S \"$BIN\" 2>/dev/null | grep -q '\\.codesign'"
c "T3 musl interpreter (no glibc loader)" "readelf -l \"$BIN\" 2>/dev/null | grep -q 'ld-musl'"

# 运行期可写 tmp 约定：OHOS /tmp 为只读 erofs，需依赖可写 TMPDIR。
# 不写死用户路径：优先 TMPDIR，其次 HOME，再退到当前目录；探针名带 $$ 防并发冲突。
tmpd="${TMPDIR:-${HOME:-.}}"
[ -w "$tmpd" ] || tmpd="."
mkdir -p "$tmpd" 2>/dev/null
probe="$tmpd/.skia-probe.$$"
c "T4 tmp dir is writable: $tmpd" "[ -w \"$tmpd\" ]"
: > "$probe" 2>/dev/null
c "T4 tmp dir accepts files" "[ -f \"$probe\" ]"
rm -f "$probe"

echo "test_ohos skia 2.88.9: $((checks - fails))/$checks checks PASS"
[ "$fails" -eq 0 ] || exit 1
exit 0
