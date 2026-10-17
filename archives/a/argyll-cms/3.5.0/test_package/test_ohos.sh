#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — argyll-cms 3.5.0 鸿蒙特有测试
#
# 参数: $1 = 被测包的 package_folder
#
# 断言（14 条）：
#   1  平台身份：uname -s = HarmonyOS，uname -m = aarch64
#   2  bin/ 下全部工具（≥47 个）为 ELF64 AArch64
#   3  全部工具为 PIE（ELF Type: DYN）
#   4  解释器为 /lib/ld-musl-aarch64.so.1（musl，非 glibc 的 ld-linux-aarch64）
#   5  无 glibc 专有 NEEDED（libc.so.6 / libm.so.6 / libpthread.so.0 / libdl.so.2 / librt.so.1）
#   6  每个工具都带 OHOS ELF 标识段 .note.ohos.ident
#   7  每个工具都带 .codesign 段（OHOS 签名占位）
#   8  RUNPATH 不指向系统库目录（/lib /usr/lib /lib64 /usr/local/lib —— R26 防系统库污染）
#   9  X11 GUI 工具（dispwin）的 NEEDED 含全部 8 个 X 库
#  10  X11 运行期加载可用：dispwin --version 打印 "Version 3.5.0"
#  11  无显示服务时优雅退出（不崩溃/不挂死）：退出码 1 且报 Unable to open the default display
#  12  ref/ 参考数据随包提供（sRGB.icm / ClayRGB1998.icm / ColorChecker.cht 等可读）
#  13  工具在任意 cwd 下可用（不依赖构建目录）
#  14  包载荷完整：bin/ ≥47 个工具、ref/ ≥90 个参考数据文件
set -euo pipefail

PKG="${1:-}"
[ -n "$PKG" ] || { echo "FAIL: usage: test_ohos.sh <package_folder>" >&2; exit 1; }
BINDIR="$PKG/bin"
REFDIR="$PKG/ref"
[ -d "$BINDIR" ] || { echo "FAIL: $BINDIR missing" >&2; exit 1; }
[ -d "$REFDIR" ] || { echo "FAIL: $REFDIR missing" >&2; exit 1; }

find_tool() {
  local name="$1" p
  p="$(command -v "$name" 2>/dev/null || true)"
  if [ -n "$p" ]; then printf '%s' "$p"; return 0; fi
  for c in /data/service/hnp/bin/"$name" /usr/bin/"$name" /bin/"$name"; do
    [ -f "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}
READELF="$(find_tool readelf)" || { echo "FAIL: readelf not found" >&2; exit 1; }
TIMEOUT="$(find_tool timeout || true)"
if [ -n "$TIMEOUT" ]; then run_tool() { "$TIMEOUT" 300 "$@"; }; else run_tool() { "$@"; }; fi

WORKDIR=""
for base in "${TMPDIR:-}" "${HOME:-}/tmp" "${HOME:-}" /tmp; do
  [ -n "$base" ] || continue
  mkdir -p "$base" 2>/dev/null || continue
  if WORKDIR="$(mktemp -d "$base/argyll-cms-ohos.XXXXXX" 2>/dev/null)"; then break; fi
done
[ -n "$WORKDIR" ] || { echo "FAIL: no writable temp directory" >&2; exit 1; }
trap 'rm -rf "$WORKDIR"' EXIT HUP INT TERM

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; exit 1; }

# 工具列表：bin/ 下的可执行文件（排除随上游 install 一起装入的文档/元数据）
TOOLS=()
for f in "$BINDIR"/*; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in
    License.txt|com.argyllcms.metainfo.xml) continue ;;
  esac
  TOOLS+=("$f")
done
[ "${#TOOLS[@]}" -ge 47 ] || fail "1x bin/ 工具数量不足: ${#TOOLS[@]} < 47"

# ── 断言 1: 平台身份 ────────────────────────────────────────────────────
OS_S="$(uname -s)"
ARCH_M="$(uname -m)"
case "$OS_S" in
  HarmonyOS|OHOS) ;;
  *) fail "1/14 uname -s = $OS_S (expected HarmonyOS/OHOS)" ;;
esac
[ "$ARCH_M" = "aarch64" ] || fail "1/14 uname -m = $ARCH_M (expected aarch64)"
ok "1/14 platform identity: $OS_S / $ARCH_M"

# ── 断言 2/3/4/6/7: 逐个工具检查 ELF 头部与关键段 ───────────────────────
NOTELF=""; NOT64=""; NOTAARCH=""; NOTPIE=""; BADINTERP=""; NOMARK=""; NOSIGN=""
for f in "${TOOLS[@]}"; do
  HDR="$("$READELF" -h "$f" 2>&1)" || { NOTELF="$NOTELF $(basename "$f")"; continue; }
  case "$HDR" in *"Class:"*"ELF64"*) ;; *) NOT64="$NOT64 $(basename "$f")" ;; esac
  case "$HDR" in *"Machine:"*"AArch64"*) ;; *) NOTAARCH="$NOTAARCH $(basename "$f")" ;; esac
  case "$HDR" in *"Type:"*"DYN"*) ;; *) NOTPIE="$NOTPIE $(basename "$f")" ;; esac
  INTERP="$("$READELF" -l "$f" 2>/dev/null | sed -n 's/.*program interpreter: \(.*\)\]/\1/p' | head -1)"
  [ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] || BADINTERP="$BADINTERP $(basename "$f"):$INTERP"
  SECS="$("$READELF" -S "$f" 2>/dev/null || true)"
  case "$SECS" in *".note.ohos.ident"*) ;; *) NOMARK="$NOMARK $(basename "$f")" ;; esac
  case "$SECS" in *".codesign"*) ;; *) NOSIGN="$NOSIGN $(basename "$f")" ;; esac
done
[ -z "$NOTELF" ]    || fail "2/14 非 ELF 文件:$NOTELF"
[ -z "$NOT64" ]     || fail "2/14 非 ELF64:$NOT64"
[ -z "$NOTAARCH" ]  || fail "2/14 非 AArch64:$NOTAARCH"
ok "2/14 all ${#TOOLS[@]} tools are ELF64 AArch64"
[ -z "$NOTPIE" ] || fail "3/14 非 PIE:$NOTPIE"
ok "3/14 all ${#TOOLS[@]} tools are PIE (Type: DYN)"
[ -z "$BADINTERP" ] || fail "4/14 解释器不是 musl loader:$BADINTERP"
ok "4/14 all tools use /lib/ld-musl-aarch64.so.1"
[ -z "$NOMARK" ] || fail "6/14 缺 .note.ohos.ident:$NOMARK"
ok "6/14 all tools carry the OHOS ELF marker .note.ohos.ident"
[ -z "$NOSIGN" ] || fail "7/14 缺 .codesign:$NOSIGN"
ok "7/14 all tools carry the .codesign section"

# ── 断言 5: 无 glibc 专有 NEEDED ────────────────────────────────────────
GLIBC_HITS=""
for f in "${TOOLS[@]}"; do
  NEEDED="$("$READELF" -d "$f" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
  for lib in $NEEDED; do
    case "$lib" in
      libc.so.6|libm.so.6|libpthread.so.0|libdl.so.2|librt.so.1|libstdc++.so.6)
        GLIBC_HITS="$GLIBC_HITS $(basename "$f"):$lib" ;;
    esac
  done
done
[ -z "$GLIBC_HITS" ] || fail "5/14 glibc 专有依赖:$GLIBC_HITS"
ok "5/14 no glibc-specific NEEDED entries (musl/OHOS libc only)"

# ── 断言 8: RUNPATH 不指向系统库目录（R26 防污染）───────────────────────
SYS_RUNPATH=""
for f in "${TOOLS[@]}"; do
  RPATH="$("$READELF" -d "$f" 2>/dev/null | sed -n 's/.*Library runpath: \[\(.*\)\]/\1/p')"
  [ -n "$RPATH" ] || continue
  IFS=':' read -r -a ENTRIES <<< "$RPATH"
  for e in "${ENTRIES[@]}"; do
    case "$e" in
      /lib|/lib64|/usr/lib|/usr/lib64|/usr/local/lib|/lib/*|/usr/lib/*|/usr/lib64/*|/usr/local/lib/*)
        SYS_RUNPATH="$SYS_RUNPATH $(basename "$f"):$e" ;;
    esac
  done
done
[ -z "$SYS_RUNPATH" ] || fail "8/14 RUNPATH 指向系统库目录:$SYS_RUNPATH"
ok "8/14 RUNPATH entries are package-private (no /lib,/usr/lib,/lib64,/usr/local/lib)"

# ── 断言 9: GUI 工具的 X11 NEEDED 集 ────────────────────────────────────
XNEEDED="$("$READELF" -d "$BINDIR/dispwin" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
for lib in libX11.so.6 libXext.so.6 libXxf86vm.so.1 libXinerama.so.1 \
           libXrandr.so.2 libXau.so.6 libXdmcp.so.6 libXss.so.1; do
  printf '%s\n' "$XNEEDED" | grep -qx "$lib" || fail "9/14 dispwin NEEDED 缺 $lib"
done
ok "9/14 dispwin links the full Conan X11 set (8 libs)"

# ── 断言 10: dispwin --version 真实运行 ─────────────────────────────────
set +e
DWIN="$(run_tool "$BINDIR/dispwin" --version 2>&1)"
set -e
case "$DWIN" in
  *"Version 3.5.0"*) ok "10/14 dispwin runs and reports Version 3.5.0" ;;
  *) fail "10/14 dispwin failed: $DWIN" ;;
esac

# ── 断言 11: 无显示服务时优雅退出 ───────────────────────────────────────
set +e
DISP_OUT="$(run_tool "$BINDIR/dispwin" 2>&1)"
DISP_RC=$?
set -e
[ "$DISP_RC" -eq 1 ] || fail "11/14 dispwin 无显示时应 rc=1，实际 rc=$DISP_RC"
case "$DISP_OUT" in
  *"Unable to open the default display"*) ok "11/14 headless dispwin exits 1 gracefully" ;;
  *) fail "11/14 dispwin 无显示时输出异常: $DISP_OUT" ;;
esac

# ── 断言 12: ref/ 参考数据随包提供 ──────────────────────────────────────
for r in sRGB.icm ClayRGB1998.icm ColorChecker.cht; do
  [ -s "$REFDIR/$r" ] || fail "12/14 ref/$r 缺失"
done
ok "12/14 packaged reference data present (sRGB.icm / ClayRGB1998.icm / ColorChecker.cht)"

# ── 断言 13: 任意 cwd 下可用（不依赖构建目录）───────────────────────────
cd "$WORKDIR"
cp "$REFDIR/sRGB.icm" .
ABS_DUMP="$(run_tool "$BINDIR/iccdump" "$WORKDIR/sRGB.icm" 2>&1)" || fail "13/14 绝对路径 iccdump rc=$?"
case "$ABS_DUMP" in
  *"Profile size    = 3004 bytes"*) ok "13/14 tools work from an arbitrary cwd with absolute paths" ;;
  *) fail "13/14 iccdump 在 $WORKDIR 下输出异常" ;;
esac

# ── 断言 14: 包载荷完整 ────────────────────────────────────────────────
NTOOLS="${#TOOLS[@]}"
NREF=$(find "$REFDIR" -maxdepth 1 -type f | wc -l)
[ "$NTOOLS" -ge 47 ] || fail "14/14 bin/ 工具数 $NTOOLS < 47"
[ "$NREF"   -ge 90 ] || fail "14/14 ref/ 参考文件数 $NREF < 90"
ok "14/14 payload complete: $NTOOLS tools + $NREF reference files"

echo "[test_ohos.sh] all 14 assertions passed"
