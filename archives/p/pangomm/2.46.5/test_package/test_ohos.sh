#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — pangomm 2.46.5 鸿蒙特有测试（14 条断言）
#
# 参数: $1 = 被测包的 package_folder
#       $2 = (可选) test_ohos_probe 可执行文件路径（默认 ./test_ohos_probe）
#
# 断言（14 条）：
#   1  平台身份：uname -s = HarmonyOS/OHOS，uname -m = aarch64
#   2  SONAME 链已物化：libpangomm-1.4.so / .so.1 / .so.1.0.30 均为普通文件
#      （OHOS 挂载点禁 symlink；缺失会导致加载器按 SONAME 查找落空）
#   3  三个文件均为 ELF64 / AArch64 / DYN（共享对象）
#   4  版本文件的 SONAME == libpangomm-1.4.so.1
#   5  三个文件均带 OHOS ELF 标识段 .note.ohos.ident
#   6  三个文件均带 .codesign 段（OHOS 签名，dlopen 前置条件 E135）
#   7  libpangomm-1.4.so.1 的 DT_NEEDED 覆盖全部 7 个 Conan 依赖
#   8  无 glibc 专有 NEEDED（libc.so.6 / libm.so.6 / libstdc++.so.6 等）
#   9  RUNPATH/RPATH 不指向系统库目录（R26 防系统库污染）
#  10  开发头文件随包提供（pangomm.h / pangomm/init.h / pangommconfig.h）
#  11  pkg-config 文件 pangomm-1.4.pc 随包提供且 Version: 2.46.5
#  12  pangomm-1.4.pc 的 Requires 含 glibmm-2.4 / cairomm-1.0 / pangocairo
#  13  运行时探针：dlopen(libpangomm-1.4.so.1, RTLD_NOW) + dlsym + 真实调用
#      Pango::init()（验证 OHOS 签名有效、依赖链可解析、符号来自被测包）
#  14  包载荷完整：>= 40 个头文件、>= 3 个 m4、1 个 .pc、许可证文件
set -euo pipefail

PKG="${1:-}"
PROBE="${2:-./test_ohos_probe}"
[ -n "$PKG" ] || { echo "FAIL: usage: test_ohos.sh <package_folder> [probe]" >&2; exit 1; }
LIBDIR="$PKG/lib"
[ -d "$LIBDIR" ] || { echo "FAIL: $LIBDIR missing" >&2; exit 1; }

find_tool() {
  local name="$1" p
  p="$(command -v "$name" 2>/dev/null || true)"
  if [ -n "$p" ]; then printf '%s' "$p"; return 0; fi
  for c in /data/service/hnp/bin/"$name" /usr/bin/"$name" /bin/"$name"; do
    [ -f "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}
READELF="$(find_tool readelf || find_tool llvm-readelf)" || { echo "FAIL: readelf not found" >&2; exit 1; }

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; exit 1; }

SO_BASE="$LIBDIR/libpangomm-1.4.so"
SO_MAJOR="$LIBDIR/libpangomm-1.4.so.1"
SO_FULL="$LIBDIR/libpangomm-1.4.so.1.0.30"

# ── 断言 1: 平台身份 ────────────────────────────────────────────────────
OS_S="$(uname -s)"
ARCH_M="$(uname -m)"
case "$OS_S" in
  HarmonyOS|OHOS) ;;
  *) fail "1/14 uname -s = $OS_S (expected HarmonyOS/OHOS)" ;;
esac
[ "$ARCH_M" = "aarch64" ] || fail "1/14 uname -m = $ARCH_M (expected aarch64)"
ok "1/14 platform identity: $OS_S / $ARCH_M"

# ── 断言 2: SONAME 链物化（普通文件，非悬空 symlink）───────────────────
for f in "$SO_BASE" "$SO_MAJOR" "$SO_FULL"; do
  [ -f "$f" ] || fail "2/14 缺失或非普通文件: $f（OHOS 挂载点禁 symlink，须物化）"
done
SIZE_BASE=$(stat -c %s "$SO_BASE")
SIZE_MAJOR=$(stat -c %s "$SO_MAJOR")
SIZE_FULL=$(stat -c %s "$SO_FULL")
[ "$SIZE_BASE" = "$SIZE_FULL" ] || fail "2/14 libpangomm-1.4.so 与版本文件大小不一致 ($SIZE_BASE vs $SIZE_FULL)"
[ "$SIZE_MAJOR" = "$SIZE_FULL" ] || fail "2/14 libpangomm-1.4.so.1 与版本文件大小不一致 ($SIZE_MAJOR vs $SIZE_FULL)"
ok "2/14 SONAME chain materialized (.so / .so.1 / .so.1.0.30, ${SIZE_FULL} bytes each)"

# ── 断言 3/4/5/6: ELF 头 + 关键段 ───────────────────────────────────────
NOTELF=""; NOT64=""; NOTAARCH=""; NOTDYN=""; BADSONAME=""; NOMARK=""; NOSIGN=""
for f in "$SO_BASE" "$SO_MAJOR" "$SO_FULL"; do
  HDR="$("$READELF" -h "$f" 2>&1)" || { NOTELF="$NOTELF $(basename "$f")"; continue; }
  case "$HDR" in *"Class:"*"ELF64"*) ;; *) NOT64="$NOT64 $(basename "$f")" ;; esac
  case "$HDR" in *"Machine:"*"AArch64"*) ;; *) NOTAARCH="$NOTAARCH $(basename "$f")" ;; esac
  case "$HDR" in *"Type:"*"DYN"*) ;; *) NOTDYN="$NOTDYN $(basename "$f")" ;; esac
  DYNS="$("$READELF" -d "$f" 2>/dev/null || true)"
  case "$DYNS" in *"Library soname: [libpangomm-1.4.so.1]"*) ;; *) BADSONAME="$BADSONAME $(basename "$f")" ;; esac
  SECS="$("$READELF" -S "$f" 2>/dev/null || true)"
  case "$SECS" in *".note.ohos.ident"*) ;; *) NOMARK="$NOMARK $(basename "$f")" ;; esac
  case "$SECS" in *".codesign"*) ;; *) NOSIGN="$NOSIGN $(basename "$f")" ;; esac
done
[ -z "$NOTELF" ]   || fail "3/14 非 ELF 文件:$NOTELF"
[ -z "$NOT64" ]    || fail "3/14 非 ELF64:$NOT64"
[ -z "$NOTAARCH" ] || fail "3/14 非 AArch64:$NOTAARCH"
[ -z "$NOTDYN" ]   || fail "3/14 非共享对象 (Type != DYN):$NOTDYN"
ok "3/14 all three are ELF64 AArch64 shared objects (Type: DYN)"
[ -z "$BADSONAME" ] || fail "4/14 SONAME 非 libpangomm-1.4.so.1:$BADSONAME"
ok "4/14 SONAME is libpangomm-1.4.so.1 on all three files"
[ -z "$NOMARK" ] || fail "5/14 缺 .note.ohos.ident:$NOMARK"
ok "5/14 all three carry the OHOS ELF marker .note.ohos.ident"
[ -z "$NOSIGN" ] || fail "6/14 缺 .codesign 段（未签名）:$NOSIGN"
ok "6/14 all three carry the .codesign section (signed for OHOS dlopen)"

# ── 断言 7: 完整依赖链 NEEDED ───────────────────────────────────────────
NEEDED="$("$READELF" -d "$SO_MAJOR" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
for lib in libglibmm-2.4.so.1 libcairomm-1.0.so.1 libsigc-2.0.so.0 \
           libpango-1.0.so.0 libpangocairo-1.0.so.0 libglib-2.0.so.0 libgobject-2.0.so.0; do
  printf '%s\n' "$NEEDED" | grep -qx "$lib" || fail "7/14 libpangomm-1.4.so.1 NEEDED 缺 $lib"
done
ok "7/14 DT_NEEDED covers all 7 Conan dependencies"

# ── 断言 8: 无 glibc 专有 NEEDED ────────────────────────────────────────
GLIBC_HITS=""
for f in "$SO_BASE" "$SO_MAJOR" "$SO_FULL"; do
  N="$("$READELF" -d "$f" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
  for lib in $N; do
    case "$lib" in
      libc.so.6|libm.so.6|libpthread.so.0|libdl.so.2|librt.so.1|libstdc++.so.6|libgcc_s.so.1)
        GLIBC_HITS="$GLIBC_HITS $(basename "$f"):$lib" ;;
    esac
  done
done
[ -z "$GLIBC_HITS" ] || fail "8/14 glibc 专有依赖:$GLIBC_HITS"
ok "8/14 no glibc-specific NEEDED entries (musl/OHOS libc only)"

# ── 断言 9: RUNPATH/RPATH 不指向系统库目录（R26）────────────────────────
# 本包产物无 RUNPATH（依赖链由 Conan 管理），故此处显式记录观测值：若未来
# 出现指向 /lib、/usr/lib、/lib64、/usr/local/lib 的 RUNPATH 条目即 FAIL。
SYS_RUNPATH=""
RPATH_SEEN=0
for f in "$SO_BASE" "$SO_MAJOR" "$SO_FULL"; do
  DYN="$("$READELF" -d "$f" 2>/dev/null || true)"
  RPATH="$(printf '%s\n' "$DYN" | sed -n 's/.*\(Library runpath\|Library rpath\|RUNPATH\|RPATH\): \[\(.*\)\]/\2/p' | head -1)"
  [ -n "$RPATH" ] || continue
  RPATH_SEEN=$((RPATH_SEEN + 1))
  IFS=':' read -r -a ENTRIES <<< "$RPATH"
  for e in "${ENTRIES[@]}"; do
    case "$e" in
      /lib|/lib64|/usr/lib|/usr/lib64|/usr/local/lib|/lib/*|/usr/lib/*|/usr/lib64/*|/usr/local/lib/*)
        SYS_RUNPATH="$SYS_RUNPATH $(basename "$f"):$e" ;;
    esac
  done
done
[ -z "$SYS_RUNPATH" ] || fail "9/14 RUNPATH 指向系统库目录:$SYS_RUNPATH"
ok "9/14 no system-dir RUNPATH (observed runpath-bearing files: $RPATH_SEEN/3)"

# ── 断言 10: 开发头文件随包提供 ─────────────────────────────────────────
for h in include/pangomm-1.4/pangomm.h \
         include/pangomm-1.4/pangomm/init.h \
         include/pangomm-1.4/pangomm/fontdescription.h \
         lib/pangomm-1.4/include/pangommconfig.h; do
  [ -f "$PKG/$h" ] || fail "10/14 缺头文件 $h"
done
ok "10/14 development headers packaged (pangomm.h / pangomm/init.h / fontdescription.h / pangommconfig.h)"

# ── 断言 11/12: pkg-config 文件 ─────────────────────────────────────────
PC="$LIBDIR/pkgconfig/pangomm-1.4.pc"
[ -f "$PC" ] || PC="$(find "$LIBDIR" -name 'pangomm-1.4.pc' 2>/dev/null | head -1)"
[ -n "$PC" ] && [ -f "$PC" ] || fail "11/14 缺 pangomm-1.4.pc"
grep -q "^Version: 2.46.5" "$PC" || fail "11/14 pangomm-1.4.pc Version 非 2.46.5: $(grep '^Version:' "$PC" || echo '(none)')"
ok "11/14 pangomm-1.4.pc present with Version: 2.46.5"
REQ="$(sed -n 's/^Requires:[[:space:]]*//p' "$PC" | head -1)"
for r in glibmm-2.4 cairomm-1.0 pangocairo; do
  printf '%s\n' "$REQ" | grep -q "$r" || fail "12/14 pangomm-1.4.pc Requires 缺 $r (Requires: $REQ)"
done
ok "12/14 pangomm-1.4.pc requires glibmm-2.4 / cairomm-1.0 / pangocairo"

# ── 断言 13: 运行时探针（dlopen + dlsym + 真实调用）─────────────────────
[ -f "$PROBE" ] || fail "13/14 探针可执行文件不存在: $PROBE"
set +e
PROBE_OUT="$("$PROBE" "$PKG" 2>&1)"
PROBE_RC=$?
set -e
[ "$PROBE_RC" -eq 0 ] || fail "13/14 OHOS dlopen 探针失败 (rc=$PROBE_RC): $PROBE_OUT"
echo "$PROBE_OUT" | tail -1 | grep -q "all .* checks passed" || fail "13/14 探针输出异常: $PROBE_OUT"
PROBE_CHECKS=$(echo "$PROBE_OUT" | tail -1 | sed -n 's/.*all \([0-9][0-9]*\) checks passed.*/\1/p')
[ "${PROBE_CHECKS:-0}" -ge 5 ] || fail "13/14 探针断言数异常: ${PROBE_CHECKS:-0}"
ok "13/14 runtime probe: dlopen(RTLD_NOW) + dlsym + Pango::init() OK ($PROBE_CHECKS checks)"

# ── 断言 14: 包载荷完整 ─────────────────────────────────────────────────
NHDR=$(find "$PKG/include" -name '*.h' 2>/dev/null | wc -l)
NM4=$(find "$PKG" -name '*.m4' 2>/dev/null | wc -l)
NPC=$(find "$PKG" -name '*.pc' 2>/dev/null | wc -l)
[ "$NHDR" -ge 40 ] || fail "14/14 头文件数 $NHDR < 40"
[ "$NM4"  -ge 3 ]  || fail "14/14 m4 文件数 $NM4 < 3"
[ "$NPC"  -ge 1 ]  || fail "14/14 缺 pkg-config 文件"
[ -s "$PKG/licenses/COPYING" ] || fail "14/14 缺许可证 COPYING"
ok "14/14 payload complete: $NHDR headers + $NM4 m4 + $NPC pc + COPYING"

[ "$PASS" -eq 14 ] || fail "断言计数异常: PASS=$PASS（期望 14，说明有断言被跳过或重复）"
echo "[test_ohos.sh] all $PASS assertions passed"
