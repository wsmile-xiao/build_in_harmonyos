#!/usr/bin/env bash
# test_package/test_ohos.sh — ctronome 0.5.6 鸿蒙（OpenHarmony PC / aarch64）平台特有测试。
#
# 由 test_package/conanfile.py 的 test() 在 `conan create` 的 test 阶段真实执行，
# $1 = 被测包里最终安装的产物 <pkg>/bin/ctronome（不是源码树中的中间产物）；
# $2（可选）= 采样目录，默认按 <bin>/../share/ctronome 推导。
#
# 所有断言 fail closed：任何非零退出 / 超时 / 缺工具都直接判失败，不做跳过。
#
# 覆盖的鸿蒙特有项（16 条）：
#   1  ELF class = ELF64
#   2  Machine = AArch64，Type = DYN（PIE）
#   3  .interp 段 == /lib/ld-musl-aarch64.so.1（musl，而非 glibc）
#   4  readelf -l 的 "Requesting program interpreter" 与 .interp 一致
#   5  无 RPATH / RUNPATH
#   6  动态依赖仅为 musl libc（NEEDED 无 glibc 专有库）
#   7  OHOS ELF 标记：.codesign ×1 + .note.ohos.ident
#   8  可加载镜像内无构建机 / SDK 构建路径
#   9  整个二进制内无本机构建路径（/storage/、/home/、/data/service/hnp、/build/）
#  10  鸿蒙 shell 约束：OHOS /system/bin/sh 无法直接 exec ELF，须经 bash 调用
#      （本包 conanfile.py 用 CONFIG_SHELL/bash 包裹执行的原因）
#  11  包内产物完备（bin + 4 个采样 WAV + README/NOTES/prog_example.txt/COPYING）
#  12  上游硬编码默认路径 /usr/share/ctronome/metronome1.wav 在 OHOS 不存在：
#      不传 -w1/-w2 时优雅报错退出（rc=1），不得崩溃
#  13  包内 WAV 采样可被真实载入（不报 too short / cannot open）
#  14  OSS /dev/dsp 平台能力缺口：解析完参数与 WAV 后打印
#      FATAL: cannot open dsp device /dev/dsp 优雅退出（rc=1，非崩溃码）
#  15  -d <自定义设备> 覆盖生效（错误信息中出现自定义设备名）
#  16  上述所有真实运行均无 crash（无 128+signal / Segmentation fault）
set -euo pipefail

BIN="${1:-}"
[ -n "$BIN" ] || { echo "FAIL: usage: test_ohos.sh <pkg>/bin/ctronome [share_dir]" >&2; exit 1; }
[ -x "$BIN" ] || { echo "FAIL: binary not executable: $BIN" >&2; exit 1; }
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"
SHARE="${2:-$(cd "$(dirname "$BIN")/../share/ctronome" && pwd)}"
LICENSES="$(cd "$(dirname "$BIN")/../licenses" && pwd)"

fail() { echo "FAIL: $*" >&2; exit 1; }

# ── 工具探测（fail closed：都找不到就直接失败，绝不静默跳过断言）──────────
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

# OHOS /system/bin/sh 不能直接 exec ELF；脚本一律由 bash 包裹执行。
BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
  BASH_BIN="$(command -v bash || true)"
fi
[ -n "$BASH_BIN" ] && [ -x "$BASH_BIN" ] \
  || fail "bash not found (CONFIG_SHELL/PATH) — required to execute ELF on OHOS"

echo "[ohos] binary : $BIN"
echo "[ohos] share  : $SHARE"
echo "[ohos] readelf: $READELF ($("$READELF" --version 2>/dev/null | head -n1 || true))"
echo "[ohos] bash   : $BASH_BIN"

TMPD="$(mktemp -d "${TMPDIR:-/tmp}/ctronome-ohos.XXXXXX")"
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

# 断言 16 的守卫：任何一次真实运行都不得以崩溃收场
CRASH_SEEN=""
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
    CRASH_SEEN="yes"
    fail "$label reported a crash marker"
  fi
}

# ── 1/16 ELF class ────────────────────────────────────────────────────────
echo "[ohos] 1/16 ELF class"
HDR="$("$READELF" -h "$BIN")"
grep -q 'Class:.*ELF64' <<<"$HDR" || fail "not ELF64"
echo "OK: 1/16 ELF class is ELF64"

# ── 2/16 machine + PIE ────────────────────────────────────────────────────
echo "[ohos] 2/16 machine / PIE"
grep -q 'Machine:.*AArch64' <<<"$HDR" || fail "not AArch64"
grep -q 'Type:.*DYN' <<<"$HDR" || fail "not a DYN (PIE) executable"
echo "OK: 2/16 AArch64 DYN (PIE)"

# ── 3/16 .interp == musl ──────────────────────────────────────────────────
echo "[ohos] 3/16 program interpreter (.interp)"
INTERP="$("$READELF" -p .interp "$BIN" | grep -oE '/lib/[A-Za-z0-9._-]+' | head -n1 || true)"
[ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] \
  || fail ".interp is '$INTERP', expected /lib/ld-musl-aarch64.so.1 (musl libc)"
echo "OK: 3/16 interpreter $INTERP (musl, not glibc)"

# ── 4/16 readelf -l interpreter line ──────────────────────────────────────
echo "[ohos] 4/16 readelf -l interpreter cross-check"
PHDRS="$("$READELF" -l "$BIN")"
grep -q 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' <<<"$PHDRS" \
  || fail "readelf -l interpreter line mismatch"
echo "OK: 4/16 readelf -l confirms /lib/ld-musl-aarch64.so.1"

# ── 5/16 no RPATH/RUNPATH ─────────────────────────────────────────────────
echo "[ohos] 5/16 RPATH/RUNPATH"
DYN="$("$READELF" -d "$BIN")"
grep -qE '\b(RPATH|RUNPATH)\b' <<<"$DYN" && fail "binary has RPATH/RUNPATH"
echo "OK: 5/16 no RPATH/RUNPATH"

# ── 6/16 NEEDED == musl libc only ─────────────────────────────────────────
echo "[ohos] 6/16 dynamic dependencies"
NEEDED="$(grep -oE 'Shared library: \[[^]]+\]' <<<"$DYN" | sed 's/.*\[\(.*\)\]/\1/' | sort -u || true)"
[ -n "$NEEDED" ] || fail "no NEEDED entries found in .dynamic"
while IFS= read -r lib; do
  [ -z "$lib" ] && continue
  case "$lib" in
    libc.so|ld-musl-aarch64.so.1) : ;;
    *) fail "non-musl dynamic dependency: $lib (NEEDED must be musl libc only)" ;;
  esac
done <<<"$NEEDED"
grep -qE 'libc\.so\.6|libpthread\.so\.0|libdl\.so\.2|librt\.so\.1|libm\.so\.6|libgcc_s\.so' <<<"$NEEDED" \
  && fail "glibc-specific library in NEEDED"
echo "OK: 6/16 NEEDED = $(tr '\n' ' ' <<<"$NEEDED")(musl libc only)"

# ── 7/16 OHOS ELF markers ─────────────────────────────────────────────────
echo "[ohos] 7/16 OHOS ELF markers"
SECS="$("$READELF" -SW "$BIN")"
NCS="$(grep -c '\.codesign' <<<"$SECS" || true)"
[ "$NCS" -eq 1 ] || fail ".codesign section count = $NCS, expected 1"
grep -q '\.note\.ohos\.ident' <<<"$SECS" || fail ".note.ohos.ident marker missing"
echo "OK: 7/16 .codesign x1 + .note.ohos.ident present"

# ── 8/16 no host/SDK build paths in the loadable image ────────────────────
echo "[ohos] 8/16 absolute paths in loadable sections"
ALLOC=""
for s in .interp .rodata .data .dynstr .dynamic; do
  # 逐段追加并补换行：避免上一段末行与下一段标题粘连（只影响证据打印）
  ALLOC="$ALLOC$("$READELF" -p "$s" "$BIN" 2>/dev/null || true)"$'\n'
done
ABSPATHS="$(grep -oE '/[A-Za-z0-9._+/-]{3,}' <<<"$ALLOC" | sort -u || true)"
echo "[info] loadable absolute paths:"; sed 's/^/        /' <<<"$ABSPATHS"
BADALLOC="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/|/devcloud/|/root/|/tmp/|/workspace/|/var/tmp/)' <<<"$ABSPATHS" || true)"
[ -z "$BADALLOC" ] || { printf '%s\n' "$BADALLOC" >&2; fail "host/SDK build path leaked into the loadable image"; }
echo "OK: 8/16 loadable image has no host/SDK build paths"

# ── 9/16 no build-machine paths anywhere in the file ──────────────────────
echo "[ohos] 9/16 build-machine paths inside the binary"
ALLSTR="$("$STRINGS" -a "$BIN")"
BADPATHS="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/)' <<<"$ALLSTR" || true)"
[ -z "$BADPATHS" ] || { head -5 <<<"$BADPATHS" >&2; fail "build-machine absolute path embedded in binary"; }
# 说明：OHOS SDK 预编译 crt 目标文件带 DWARF，debug 段里会留下 SDK 自身的
# 构建路径（/devcloud/...）。它不在任何可加载段（断言 8 已证明），也不属于
# 本机构建路径，故不计为缺陷；此处仅记录条数作为证据。
echo "[info] DWARF-only SDK build path occurrences: $(grep -c 'devcloud' <<<"$ALLSTR" || true) (debug sections only)"
echo "OK: 9/16 no build-machine absolute path in binary"

# ── 10/16 bash-wrapped execution (OHOS shell constraint) ─────────────────
echo "[ohos] 10/16 bash-wrapped execution"
set +e
WRAP_OUT="$("$BASH_BIN" -c "\"$BIN\" -h" 2>&1)"
WRAP_RC=$?
set -e
[ "$WRAP_RC" -eq 0 ] || { printf '%s\n' "$WRAP_OUT" >&2; fail "bash-wrapped -h failed (rc=$WRAP_RC)"; }
grep -q 'usage: ctronome' <<<"$WRAP_OUT" || fail "bash-wrapped -h did not print usage"
set +e
PLAIN_OUT="$(/usr/bin/sh -c "\"$BIN\" -h" 2>&1)"
PLAIN_RC=$?
set -e
echo "[info] plain /usr/bin/sh direct exec rc=$PLAIN_RC (OHOS /system/bin/sh cannot exec ELF; always wrap with bash)"
echo "OK: 10/16 bash -c \"ctronome -h\" works (rc=0)"

# ── 11/16 packaged artifacts ──────────────────────────────────────────────
echo "[ohos] 11/16 packaged artifacts"
for f in metronome1.wav metronome2.wav metronome1_stereo.wav metronome2_stereo.wav \
         README NOTES prog_example.txt; do
  [ -f "$SHARE/$f" ] || fail "missing packaged file: $SHARE/$f"
done
[ -f "$LICENSES/COPYING" ] || fail "missing licenses/COPYING"
echo "OK: 11/16 package ships 4 WAV samples + docs + COPYING"

# ── 12/16 upstream default /usr/share path absent on OHOS ────────────────
echo "[ohos] 12/16 upstream default WAV path (/usr/share) on OHOS"
[ -e /usr/share/ctronome/metronome1.wav ] \
  && fail "platform premise broken: /usr/share/ctronome/metronome1.wav exists on OHOS"
run_bin
no_crash "run without -w1/-w2"
[ "$RUN_RC" -eq 1 ] || { printf '%s\n' "$RUN_OUT" >&2; fail "expected graceful rc=1 without -w1/-w2, got rc=$RUN_RC"; }
grep -qF 'cannot open /usr/share/ctronome/metronome1.wav' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "expected graceful diagnostic naming the missing default path"; }
echo "OK: 12/16 default /usr/share path missing -> graceful exit rc=1, no crash"

# ── 13..15 real runs with the packaged samples ───────────────────────────
WAV1="$SHARE/metronome1.wav"
WAV2="$SHARE/metronome2.wav"

echo "[ohos] 13/16 packaged WAV samples load"
run_bin -b 120 -t 4 -c 1 -w1 "$WAV1" -w2 "$WAV2"
no_crash "run with packaged samples"
grep -q 'too short' <<<"$RUN_OUT" && { printf '%s\n' "$RUN_OUT" >&2; fail "packaged WAV rejected as too short"; }
grep -qF "cannot open $WAV1" <<<"$RUN_OUT" && fail "could not open $WAV1"
grep -qF "cannot open $WAV2" <<<"$RUN_OUT" && fail "could not open $WAV2"
grep -q 'the two WAV files must have' <<<"$RUN_OUT" && fail "packaged WAV pair rejected (channel/bit mismatch)"
echo "OK: 13/16 packaged WAV samples parsed successfully"

echo "[ohos] 14/16 OSS /dev/dsp platform capability gap"
[ -e /dev/dsp ] && fail "platform premise broken: /dev/dsp exists on OHOS PC"
[ "$RUN_RC" -eq 1 ] || { printf '%s\n' "$RUN_OUT" >&2; fail "expected graceful rc=1 after WAV parse, got rc=$RUN_RC"; }
grep -qF 'FATAL: cannot open dsp device /dev/dsp' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "expected FATAL dsp diagnostic (proves audio-output stage reached)"; }
echo "OK: 14/16 /dev/dsp absent -> 'FATAL: cannot open dsp device /dev/dsp', rc=1, no crash"

echo "[ohos] 15/16 -d device override"
PROBE_DEV="/dev/ctronome-ohos-probe"
run_bin -b 120 -t 4 -c 1 -w1 "$WAV1" -w2 "$WAV2" -d "$PROBE_DEV"
no_crash "run with -d override"
[ "$RUN_RC" -eq 1 ] || { printf '%s\n' "$RUN_OUT" >&2; fail "expected graceful rc=1 with -d override, got rc=$RUN_RC"; }
grep -qF "cannot open dsp device $PROBE_DEV" <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" >&2; fail "-d override not honoured (expected $PROBE_DEV in diagnostic)"; }
echo "OK: 15/16 -d override honoured (diagnostic names $PROBE_DEV)"

# ── 16/16 aggregate crash-free ───────────────────────────────────────────
echo "[ohos] 16/16 crash-free summary"
[ -z "$CRASH_SEEN" ] || fail "a ctronome run crashed during this test"
echo "OK: 16/16 all 3 real runs exited gracefully (no signals, no core dump)"

echo "OHOS ASSERTIONS PASSED: 16/16"
echo "ALL OHOS TESTS PASSED"
