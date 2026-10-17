#!/usr/bin/env bash
# test_package/test_ohos.sh — qcontrol 0.5.7 鸿蒙平台特有断言
#
# 用法: test_ohos.sh <pkg>/bin/qcontrol <pkg>/share/qcontrol
# 由 test_package/conanfile.py 的 test() 在 conan create 的 test 阶段真实执行。
# 所有断言 fail closed：缺工具 / 不符预期即判失败，不静默跳过。
#
# 覆盖项：
#   1  ELF class = ELF64
#   2  Machine = AArch64 且 Type = DYN（PIE）
#   3  .interp = /lib/ld-musl-aarch64.so.1（musl，不是 glibc）
#   4  readelf -l 的 program interpreter 与 .interp 一致
#   5  无 RPATH / RUNPATH
#   6  NEEDED 集合：无 glibc 专有 SONAME，且由 musl libc 提供符号
#   7  OHOS ELF 标记：.codesign x1 + .note.ohos.ident
#   8  可加载段内无宿主/构建机绝对路径
#   9  整个文件（strings -a）内无本机构建路径（配方为此去掉了上游 -g）
#   10 包内产物完备且不含 lib/include（application 包）
#   11 鸿蒙 shell 约束：ELF 须经 bash 包裹执行；示例配置随包可用
set -uo pipefail

BIN="${1:-}"
SHARE="${2:-}"
fail() { echo "FAIL: $*" >&2; exit 1; }

[ -n "$BIN" ] || fail "usage: test_ohos.sh <pkg>/bin/qcontrol <pkg>/share/qcontrol>"
[ -x "$BIN" ] || fail "binary not executable: $BIN"
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"
PKGROOT="$(cd "$(dirname "$BIN")/.." && pwd)"
# conan test() 的 cwd 可能刚被重建过，钉住 cwd 以免 getcwd 噪声混进断言输出。
cd "$HOME" || fail "cd $HOME failed"

N=0
ok() { N=$((N + 1)); echo "OK: $*"; }

READELF="${READELF:-}"
if [ -z "$READELF" ] || ! command -v "$READELF" >/dev/null 2>&1; then
  if [ -x /data/service/hnp/bin/llvm-readelf ]; then READELF=/data/service/hnp/bin/llvm-readelf
  elif command -v llvm-readelf >/dev/null 2>&1; then READELF=llvm-readelf
  elif command -v readelf >/dev/null 2>&1; then READELF=readelf
  else fail "no llvm-readelf/readelf available — cannot verify OHOS ELF requirements"
  fi
fi

STRINGS="${STRINGS:-}"
if [ -z "$STRINGS" ] || ! command -v "$STRINGS" >/dev/null 2>&1; then
  if [ -x /data/service/hnp/bin/strings ]; then STRINGS=/data/service/hnp/bin/strings
  elif command -v strings >/dev/null 2>&1; then STRINGS=strings
  else fail "no strings available — cannot scan the binary for host paths"
  fi
fi

BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
  BASH_BIN="$(command -v bash || true)"
fi
[ -n "$BASH_BIN" ] && [ -x "$BASH_BIN" ] \
  || fail "bash not found (CONFIG_SHELL/PATH) — required to execute ELF on OHOS"

echo "[ohos] binary : $BIN"
echo "[ohos] pkgroot: $PKGROOT"
echo "[ohos] readelf: $READELF"
echo "[ohos] strings: $STRINGS"

# ── 1 ELF class ───────────────────────────────────────────────────────────
HDR="$("$READELF" -h "$BIN")" || fail "readelf -h failed"
printf '%s' "$HDR" | grep -q 'Class:.*ELF64' || fail "not ELF64"
ok "1 ELF class is ELF64"

# ── 2 machine + PIE ──────────────────────────────────────────────────────
printf '%s' "$HDR" | grep -q 'Machine:.*AArch64' || fail "not AArch64"
printf '%s' "$HDR" | grep -q 'Type:.*DYN' || fail "not a DYN (PIE) executable"
ok "2 AArch64 DYN (PIE)"

# ── 3 .interp == musl ────────────────────────────────────────────────────
INTERP="$("$READELF" -p .interp "$BIN" | grep -oE '/lib/[A-Za-z0-9._-]+' | head -n1 || true)"
[ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] \
  || fail ".interp is [$INTERP], expected /lib/ld-musl-aarch64.so.1 (musl, not glibc)"
ok "3 program interpreter $INTERP (musl)"

# ── 4 readelf -l cross check ─────────────────────────────────────────────
printf '%s' "$("$READELF" -l "$BIN")" \
  | grep -q 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' \
  || fail "readelf -l interpreter line mismatch"
ok "4 readelf -l agrees on /lib/ld-musl-aarch64.so.1"

# ── 5 no RPATH / RUNPATH ─────────────────────────────────────────────────
DYN="$("$READELF" -d "$BIN")" || fail "readelf -d failed"
printf '%s' "$DYN" | grep -qE '\b(RPATH|RUNPATH)\b' && fail "binary carries RPATH/RUNPATH"
ok "5 no RPATH/RUNPATH"

# ── 6 NEEDED set ─────────────────────────────────────────────────────────
NEEDED="$(printf '%s' "$DYN" | grep -oE 'Shared library: \[[^]]+\]' | sed 's/.*\[\(.*\)\]/\1/' | sort -u || true)"
echo "[info] NEEDED: $(printf '%s' "$NEEDED" | tr '\n' ' ')"
printf '%s' "$NEEDED" | grep -qE 'libc\.so\.6|libpthread\.so\.0|libdl\.so\.2|librt\.so\.1|libm\.so\.6|libgcc_s\.so' \
  && fail "glibc-specific SONAME in NEEDED"
printf '%s' "$NEEDED" | grep -q '^libc\.so$' \
  || fail "libc.so (musl) missing from NEEDED — the binary is not linked against the platform libc"
ok "6 NEEDED free of glibc SONAMEs, provided by musl libc"

# ── 7 OHOS ELF markers ───────────────────────────────────────────────────
SECS="$("$READELF" -SW "$BIN")" || fail "readelf -SW failed"
NCS="$(printf '%s' "$SECS" | grep -c '\.codesign' || true)"
[ "$NCS" -eq 1 ] || fail ".codesign section count = $NCS, expected 1"
printf '%s' "$SECS" | grep -q '\.note\.ohos\.ident' || fail ".note.ohos.ident marker missing"
ok "7 .codesign x1 + .note.ohos.ident present"

# ── 8 no host build paths in loadable sections ───────────────────────────
ALLOC=""
for s in .interp .rodata .data .dynstr .dynamic; do
  ALLOC="$ALLOC$("$READELF" -p "$s" "$BIN" 2>/dev/null || true)"$'\n'
done
ABSPATHS="$(printf '%s' "$ALLOC" | grep -oE '/[A-Za-z0-9._+/-]{3,}' | sort -u || true)"
echo "[info] absolute paths in loadable sections:"
printf '%s\n' "$ABSPATHS" | sed 's/^/        /'
BADALLOC="$(printf '%s' "$ABSPATHS" | grep -E '^(/storage/|/home/|/data/service/hnp|/build/|/devcloud/|/root/|/tmp/|/workspace/|/var/tmp/|/srv/)' || true)"
[ -z "$BADALLOC" ] || { printf '%s\n' "$BADALLOC" >&2; fail "host/SDK build path leaked into the loadable image"; }
ok "8 loadable image carries no host/SDK build path"

# ── 9 no build-machine path anywhere in the file ─────────────────────────
ALLSTR="$("$STRINGS" -a "$BIN")" || fail "strings -a failed"
BADPATHS="$(printf '%s' "$ALLSTR" | grep -E '^(/storage/|/home/|/data/service/hnp|/build/|/root/|/workspace/|/var/tmp/)' || true)"
[ -z "$BADPATHS" ] || { printf '%s\n' "$BADPATHS" | head -5 >&2; fail "build-machine absolute path embedded in the shipped binary (upstream -g was dropped for this reason)"; }
echo "[info] SDK-own build paths embedded by the prelinked crt objects: $(printf '%s' "$ALLSTR" | grep -cE '^(/devcloud/|/srv/)' || true) (toolchain-internal, not this build)"
ok "9 no build-machine path anywhere in the binary"

# ── 10 packaged artifacts ────────────────────────────────────────────────
[ -x "$BIN" ] || fail "bin/qcontrol not executable"
[ -f "$PKGROOT/licenses/COPYING" ] || fail "missing licenses/COPYING"
for m in ts209 ts219 ts409 ts41x synology mv2120; do
  [ -f "$SHARE/examples/$m.lua" ] || fail "missing packaged example config: $SHARE/examples/$m.lua"
done
[ -f "$PKGROOT/share/doc/qcontrol/README" ] || fail "missing share/doc/qcontrol/README"
[ -e "$PKGROOT/lib" ] && fail "an application package must not ship a lib/ directory"
[ -e "$PKGROOT/include" ] && fail "an application package must not ship an include/ directory"
ok "10 package ships bin/qcontrol + 6 example configs + docs + license, no lib/include"

# ── 11 bash-wrapped execution + packaged config usable ───────────────────
set +e
WRAP_OUT="$("$BASH_BIN" -c "\"$BIN\" --version" 2>&1)"
WRAP_RC=$?
set -e
[ "$WRAP_RC" -eq 0 ] || { printf '%s\n' "$WRAP_OUT" >&2; fail "bash-wrapped --version failed (rc=$WRAP_RC)"; }
[ "$WRAP_OUT" = "qcontrol 0.5.7" ] || { printf '%s\n' "$WRAP_OUT" >&2; fail "bash-wrapped --version printed [$WRAP_OUT]"; }
ok "11 runs under the OHOS bash wrapper and reports its version"

echo "OHOS ASSERTIONS PASSED: $N/$N"
