#!/usr/bin/env bash
# test_package/test_ohos.sh — miruo 0.9.6b 鸿蒙（OpenHarmony PC / aarch64）平台特有测试。
#
# 由 test_package/conanfile.py 的 test() 在 `conan create` 的 test 阶段真实执行，
# $1 = 被测包里最终安装的产物 <pkg>/bin/miruo（不是源码树中的中间产物）。
#
# 所有断言 fail closed：任何非零退出 / 超时 / 缺工具都直接判失败，不做跳过。
#
# 覆盖的鸿蒙特有项（9 条）：
#   1  ELF class = ELF64，Machine = AArch64，Type = DYN（PIE）
#   2  .interp 段 == /lib/ld-musl-aarch64.so.1（musl，而非 glibc）
#   3  无 RPATH / RUNPATH（静态链入 libpcap，无需运行时搜索路径）
#   4  动态依赖仅为 libc.so（libpcap 静态链入，无 libpcap.so NEEDED）
#   5  OHOS ELF 标记：.codesign ×1 + .note.ohos.ident
#   6  Release 产物无本机构建路径泄漏（/storage/、/home/、
#      /data/service/hnp、/build/）
#   7  `miruo -V` 真实运行：打印 "miruo version"（上游打包缺陷：内嵌版本串
#      为 0.9.6a——configure 未随 tag 重新生成；此处断言横幅格式而非数字）
#   8  `miruo -h` 打印用法并优雅退出（rc 见下）
#   9  `miruo -i nonexist0`：不存在的接口 → pcap 错误诊断 + 优雅退出 rc=1，
#      证明 pcap_open_live 代码路径在 OHOS 上真实执行（无崩溃）
set -euo pipefail

BIN="${1:-}"
[ -n "$BIN" ] || { echo "FAIL: usage: test_ohos.sh <pkg>/bin/miruo" >&2; exit 1; }
[ -x "$BIN" ] || { echo "FAIL: binary not executable: $BIN" >&2; exit 1; }
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"

fail() { echo "FAIL: $*" >&2; exit 1; }

# ── 工具探测（fail closed）────────────────────────────────────────────
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
  else fail "no strings available — cannot scan binary for host paths"
  fi
fi

echo "[ohos] binary : $BIN"
echo "[ohos] readelf: $READELF ($("$READELF" --version 2>/dev/null | head -n1 || true))"
echo "[ohos] strings: $STRINGS"

TMPD="$(mktemp -d "${TMPDIR:-/tmp}/miruo-ohos.XXXXXX")"
trap 'rm -rf "$TMPD"' EXIT HUP INT TERM

# 真实运行被测二进制：捕获 stdout+stderr 与退出码（不因非零退出中止脚本）
RUN_OUT=""
RUN_RC=0
run_bin() {
  set +e
  RUN_OUT="$(timeout 60 "$BIN" "$@" 2>&1)"
  RUN_RC=$?
  set -e
}

# 任何一次真实运行都不得以崩溃收场
no_crash() {
  local label="$1"
  if [ "$RUN_RC" -eq 124 ]; then
    printf '%s\n' "$RUN_OUT" >&2; fail "$label timed out after 60s"
  fi
  if [ "$RUN_RC" -ge 128 ]; then
    printf '%s\n' "$RUN_OUT" >&2
    fail "$label died from a signal (rc=$RUN_RC) — crashing on OHOS"
  fi
  if grep -qE 'Segmentation fault|core dumped|Bus error|Aborted|Illegal instruction' <<<"$RUN_OUT"; then
    printf '%s\n' "$RUN_OUT" >&2
    fail "$label reported a crash marker"
  fi
}

# ── 1/9 ELF class / machine / PIE ─────────────────────────────────────
echo "[ohos] 1/9 ELF class / machine / PIE"
HDR="$("$READELF" -h "$BIN")"
grep -q 'Class:.*ELF64' <<<"$HDR" || fail "not ELF64"
grep -q 'Machine:.*AArch64' <<<"$HDR" || fail "not AArch64"
grep -q 'Type:.*DYN' <<<"$HDR" || fail "not a DYN (PIE) executable"
echo "OK: 1/9 ELF64 / AArch64 / DYN (PIE)"

# ── 2/9 .interp == musl ───────────────────────────────────────────────
echo "[ohos] 2/9 program interpreter (.interp)"
INTERP="$("$READELF" -p .interp "$BIN" | grep -oE '/lib/[A-Za-z0-9._-]+' | head -n1 || true)"
[ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] \
  || fail ".interp is '$INTERP', expected /lib/ld-musl-aarch64.so.1 (musl libc)"
echo "OK: 2/9 interpreter $INTERP (musl, not glibc)"

# ── 3/9 no RPATH/RUNPATH ──────────────────────────────────────────────
echo "[ohos] 3/9 RPATH/RUNPATH"
DYN="$("$READELF" -d "$BIN")"
grep -qE '\b(RPATH|RUNPATH)\b' <<<"$DYN" && fail "binary has RPATH/RUNPATH"
echo "OK: 3/9 no RPATH/RUNPATH"

# ── 4/9 NEEDED == libc.so only ────────────────────────────────────────
echo "[ohos] 4/9 dynamic dependencies"
NEEDED="$(grep -oE 'Shared library: \[[^]]+\]' <<<"$DYN" | sed 's/.*\[\(.*\)\]/\1/' | sort -u || true)"
[ -n "$NEEDED" ] || fail "no NEEDED entries found in .dynamic"
while IFS= read -r lib; do
  [ -z "$lib" ] && continue
  case "$lib" in
    libc.so) : ;;
    *) fail "unexpected dynamic dependency: $lib (NEEDED must be libc.so only — libpcap is statically linked)" ;;
  esac
done <<<"$NEEDED"
echo "OK: 4/9 NEEDED = $(tr '\n' ' ' <<<"$NEEDED")(libpcap statically linked)"

# ── 5/9 OHOS ELF markers ──────────────────────────────────────────────
echo "[ohos] 5/9 OHOS ELF markers"
SECS="$("$READELF" -SW "$BIN")"
NCS="$(grep -c '\.codesign' <<<"$SECS" || true)"
[ "$NCS" -eq 1 ] || fail ".codesign section count = $NCS, expected 1"
grep -q '\.note\.ohos\.ident' <<<"$SECS" || fail ".note.ohos.ident marker missing"
echo "OK: 5/9 .codesign x1 + .note.ohos.ident present"

# ── 6/9 no build-machine paths in the binary ──────────────────────────
echo "[ohos] 6/9 build-machine paths inside the binary"
ALLSTR="$("$STRINGS" -a "$BIN")"
BADPATHS="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/)' <<<"$ALLSTR" || true)"
[ -z "$BADPATHS" ] || { head -5 <<<"$BADPATHS" >&2; fail "build-machine absolute path embedded in binary"; }
# 说明：OHOS SDK 预编译 crt 目标文件带 DWARF，debug 段里会留下 SDK 自身
# 的构建路径（/devcloud/...）。它不在任何可加载段，也不属于本机构建路径，
# 故不计为缺陷；此处仅记录条数作为证据。
echo "[info] DWARF-only SDK build path occurrences: $(grep -c 'devcloud' <<<"$ALLSTR" || true) (debug sections only)"
echo "OK: 6/9 no build-machine absolute path in binary"

# ── 7/9 `miruo -V` real run ───────────────────────────────────────────
echo "[ohos] 7/9 real run: miruo -V (version banner)"
run_bin -V
no_crash "miruo -V"
grep -q 'miruo version' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "-V did not print the version banner"; }
# 上游打包缺陷：0.9.6b tag 的 configure 未重新生成，内嵌版本串为 0.9.6a。
# 断言横幅格式而非数字（如断言 0.9.6b 会对正确构建误报失败）。
echo "[info] -V banner: $(head -n1 <<<"$RUN_OUT") (upstream defect: configure not regenerated for 0.9.6b tag)"
echo "OK: 7/9 -V prints version banner"

# ── 8/9 `miruo -h` real run ───────────────────────────────────────────
echo "[ohos] 8/9 real run: miruo -h (usage)"
run_bin -h
no_crash "miruo -h"
grep -qi 'usage' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "-h did not print usage"; }
echo "OK: 8/9 -h prints usage"

# ── 9/9 `miruo -i nonexist0` real run (pcap error path) ───────────────
echo "[ohos] 9/9 real run: miruo -i nonexist0 (nonexistent interface)"
run_bin -i nonexist0
no_crash "miruo -i nonexist0"
[ "$RUN_RC" -eq 1 ] \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "expected rc=1 for nonexistent interface, got rc=$RUN_RC"; }
# pcap_open_live 对不存在接口的诊断（libpcap 1.10.6 OHOS 包：No such device...）
printf '%s\n' "$RUN_OUT" | head -n3
grep -qiE 'nonexist0|no such device|failed|error' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "expected a pcap diagnostic naming the interface"; }
echo "OK: 9/9 -i nonexistent interface -> pcap diagnostic, graceful rc=1"

echo "OHOS ASSERTIONS PASSED: 9/9"
echo "ALL OHOS TESTS PASSED"
