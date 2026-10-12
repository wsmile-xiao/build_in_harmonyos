#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — parted 3.8 鸿蒙特有测试（R53）
#
# 参数: $1 = 被测包的 package_folder
#
# 断言（13 条）：
#   1  平台身份：HarmonyOS / aarch64
#   2  bin/parted、bin/partprobe 已打包
#   3  两个工具均为 ELF64 AArch64
#   4  两个工具均为 PIE（ELF Type: DYN）
#   5  解释器为 /lib/ld-musl-aarch64.so.1（musl）
#   6  无 glibc 专有 NEEDED（libc.so.6/libm.so.6/...）
#   7  两个工具均带 OHOS ELF 标识段 .note.ohos.ident
#   8  两个工具均带 .codesign 段
#   9  RUNPATH/RPATH 不指向系统库目录（先归一化重复斜杠，再比对 /lib 等系统目录）
#  10  parted 的 NEEDED 含 libparted.so.2，且包内 lib/ 提供该实体文件
#  11  libparted.so.2 为 ELF64 AArch64，SONAME=libparted.so.2
#  12  任意 cwd 下可执行（不依赖构建目录）
#  13  包载荷完整：bin/{parted,partprobe} + lib/libparted.so.2 + include/parted/parted.h
set -euo pipefail

PKG="${1:-}"
[ -n "$PKG" ] && [ -d "$PKG" ] || { echo "FAIL: usage: test_ohos.sh <package_folder>" >&2; exit 1; }
BINDIR="$PKG/bin"
LIBDIR="$PKG/lib"
[ -d "$BINDIR" ] || { echo "FAIL: $BINDIR missing" >&2; exit 1; }
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
READELF="$(find_tool readelf)" || { echo "FAIL: readelf not found" >&2; exit 1; }

WORK=""
for base in "${TMPDIR:-}" "${HOME:-}/tmp" "${HOME:-}"; do
  [ -n "$base" ] || continue
  mkdir -p "$base" 2>/dev/null || continue
  if WORK="$(mktemp -d "$base/parted-ohos.XXXXXX" 2>/dev/null)"; then break; fi
done
[ -n "$WORK" ] || { echo "FAIL: no writable temp directory" >&2; exit 1; }
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; exit 1; }

PARTED="$BINDIR/parted"
PARTPROBE="$BINDIR/partprobe"
LIBP="$LIBDIR/libparted.so.2"
TOOLS=("$PARTED" "$PARTPROBE")

# ── 1: 平台身份 ────────────────────────────────────────────────────────
OS_S="$(uname -s)"; ARCH_M="$(uname -m)"
case "$OS_S" in HarmonyOS|OHOS) ;; *) fail "1/13 uname -s = $OS_S" ;; esac
[ "$ARCH_M" = "aarch64" ] || fail "1/13 uname -m = $ARCH_M"
ok "1/13 platform identity: $OS_S / $ARCH_M"

# ── 2: 工具存在 ────────────────────────────────────────────────────────
for f in "${TOOLS[@]}"; do
  [ -s "$f" ] || fail "2/13 missing binary: $f"
done
ok "2/13 packaged binaries: bin/parted bin/partprobe"

# ── 3/4/5/6/7/8: 逐个工具检查 ELF ─────────────────────────────────────
for f in "${TOOLS[@]}"; do
  n="$(basename "$f")"
  HDR="$("$READELF" -h "$f" 2>&1)" || fail "3/13 readelf failed: $n"
  case "$HDR" in *"Class:"*"ELF64"*) ;; *) fail "3/13 not ELF64: $n" ;; esac
  case "$HDR" in *"Machine:"*"AArch64"*) ;; *) fail "3/13 not AArch64: $n" ;; esac

  case "$HDR" in *"Type:"*"DYN"*) ;; *) fail "4/13 not PIE: $n" ;; esac

  INTERP="$("$READELF" -l "$f" 2>/dev/null | sed -n 's/.*program interpreter: \(.*\)\]/\1/p' | head -1)"
  [ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] || fail "5/13 bad interpreter ($INTERP): $n"

  NEEDED="$("$READELF" -d "$f" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
  for lib in $NEEDED; do
    case "$lib" in
      libc.so.6|libm.so.6|libpthread.so.0|libdl.so.2|librt.so.1|libstdc++.so.6)
        fail "6/13 glibc-specific NEEDED ($lib): $n" ;;
    esac
  done

  SECS="$("$READELF" -S "$f" 2>/dev/null || true)"
  case "$SECS" in *".note.ohos.ident"*) ;; *) fail "7/13 missing .note.ohos.ident: $n" ;; esac
  case "$SECS" in *".codesign"*) ;; *) fail "8/13 missing .codesign: $n" ;; esac
done
ok "3/13 both tools are ELF64 AArch64"
ok "4/13 both tools are PIE (Type: DYN)"
ok "5/13 both use /lib/ld-musl-aarch64.so.1"
ok "6/13 no glibc-specific NEEDED entries"
ok "7/13 both carry .note.ohos.ident"
ok "8/13 both carry .codesign"

# ── 9: RUNPATH/RPATH 不含系统库目录 ────────────────────────────────────
# POSIX 下 //lib ≡ /lib：先归一化重复斜杠再比对，防 //lib、///lib 漏检（W4 P1）
norm_dir() { printf '%s' "$1" | sed 's,//*,/,g'; }
LIBPFS="$LIBDIR/libparted-fs-resize.so.0"
for f in "${TOOLS[@]}" "$LIBP" "$LIBPFS"; do
  [ -e "$f" ] || continue
  DTAGS="$("$READELF" -d "$f" 2>/dev/null | sed -n 's/.*Library r\(un\)\?path: \[\(.*\)\]/\2/p')"
  [ -n "$DTAGS" ] || continue
  while IFS= read -r dtag; do
    [ -n "$dtag" ] || continue
    IFS=':' read -r -a ENTRIES <<< "$dtag"
    for e in "${ENTRIES[@]}"; do
      n="$(norm_dir "$e")"
      case "$n" in
        ""|/|/lib|/lib64|/usr/lib|/usr/lib64|/usr/local/lib|/usr/libexec|\
        /bin|/sbin|/usr/bin|/usr/sbin|/lib/*|/lib64/*|/usr/lib/*|\
        /usr/lib64/*|/usr/local/lib/*|/usr/libexec/*)
          fail "9/13 $(basename "$f") DT_RUNPATH/DT_RPATH points into system dir [$e] (normalized [$n])" ;;
      esac
    done
  done <<< "$DTAGS"
done
ok "9/13 RUNPATH/RPATH entries avoid system library directories (normalized //)"

# ── 10/11: libparted ───────────────────────────────────────────────────
[ -s "$LIBP" ] || fail "10/13 package lib/libparted.so.2 missing"
NEEDED="$("$READELF" -d "$PARTED" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
printf '%s\n' "$NEEDED" | grep -qx "libparted.so.2" || fail "10/13 parted NEEDED lacks libparted.so.2"
ok "10/13 parted NEEDED includes libparted.so.2 and package provides it"

HDR="$("$READELF" -h "$LIBP" 2>&1)"
case "$HDR" in *"Class:"*"ELF64"*) ;; *) fail "11/13 libparted not ELF64" ;; esac
case "$HDR" in *"Machine:"*"AArch64"*) ;; *) fail "11/13 libparted not AArch64" ;; esac
SONAME="$("$READELF" -d "$LIBP" 2>/dev/null | sed -n 's/.*SONAME.*\[\(.*\)\]/\1/p' | head -1)"
[ "$SONAME" = "libparted.so.2" ] || fail "11/13 SONAME = $SONAME"
ok "11/13 libparted.so.2 is ELF64 AArch64 (SONAME libparted.so.2)"

# ── 12: 任意 cwd 可执行 ────────────────────────────────────────────────
cd "$WORK"
out="$("$PARTED" --version 2>&1)" || fail "12/13 run from $WORK rc=$?"
case "$out" in *"parted (GNU parted) 3.8"*) ok "12/13 runs from arbitrary cwd" ;;
  *) fail "12/13 unexpected output: $out" ;;
esac

# ── 13: 载荷完整 ───────────────────────────────────────────────────────
[ -s "$PARTED" ] || fail "13/13 bin/parted missing"
[ -s "$PARTPROBE" ] || fail "13/13 bin/partprobe missing"
[ -s "$LIBP" ] || fail "13/13 lib/libparted.so.2 missing"
[ -s "$PKG/include/parted/parted.h" ] || fail "13/13 include/parted/parted.h missing"
ok "13/13 payload complete: bin/parted bin/partprobe lib/libparted.so.2 include/parted/parted.h"

echo "[test_ohos.sh] all 13 assertions passed"
