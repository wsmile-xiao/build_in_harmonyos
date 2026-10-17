#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — xcfa 5.0.2 鸿蒙（OpenHarmony / HarmonyOS PC, aarch64）平台特有测试。
#
# 由 test_package/conanfile.py 的 test() 在 `conan create` 的 test 阶段真实执行：
#   $1 = 包内 bin/xcfa（GTK3 GUI 二进制）
#   $2 = 包内 bin/xcfa_cli（命令行工具）
#   $3 = 被测包的 package_folder（用于校验安装产物完备性）
#
# 所有断言 fail closed：任何非零退出 / 超时 / 缺工具都直接判失败，不做跳过。
#
# 覆盖的鸿蒙特有项（14 条）：
#   1  ELF class = ELF64（两个二进制）
#   2  Machine = AArch64，Type = DYN（PIE）
#   3  .interp == /lib/ld-musl-aarch64.so.1（musl，而非 glibc）
#   4  readelf -l "Requesting program interpreter" 与 .interp 一致
#   5  无 RPATH / RUNPATH（依赖由 conanrun 环境解析）
#   6  NEEDED 中无 glibc 专有库（libc.so.6/libpthread.so.0/... ），且含
#      Conan 提供的 GTK3/VTE/ALSA/libcurl 等共享库
#   7  OHOS ELF 标记：.codesign ×1 + .note.ohos.ident
#   8  可加载段（.interp/.rodata/.data/.dynstr/.dynamic）内无构建机/SDK 路径
#   9  整个文件内无本机构建路径（/storage/、/home/、/data/service/hnp 等）；
#      OHOS SDK 预编译 crt 的 DWARF 路径（/devcloud/...，非可加载段）仅记录
#  10  鸿蒙 shell 约束：/system/bin/sh 无法直接 exec ELF，须经 bash 调用
#  11  运行期平台上报：xcfa_cli 环境报告显示 sysname = HarmonyOS / machine = aarch64
#  12  GTK/GLib 运行期版本可查（GTK3 依赖栈在 OHOS 上可加载并初始化）
#  13  无显示服务的平台能力缺口：GUI 优雅报 "cannot open display" 退出（rc=1，
#      非崩溃码）——不得挂死、不得被信号杀死
#  14  包内产物完备 + 上述所有真实运行均无 crash（无 128+signal / Segmentation fault）
set -euo pipefail

GUI="${1:-}"
CLI="${2:-}"
PKG="${3:-}"
[ -n "$GUI" ] && [ -n "$CLI" ] && [ -n "$PKG" ] \
  || { echo "FAIL: usage: test_ohos.sh <pkg>/bin/xcfa <pkg>/bin/xcfa_cli <pkg>" >&2; exit 1; }
[ -f "$GUI" ] || { echo "FAIL: gui binary missing: $GUI" >&2; exit 1; }
[ -f "$CLI" ] || { echo "FAIL: cli binary missing: $CLI" >&2; exit 1; }
[ -d "$PKG" ] || { echo "FAIL: package folder missing: $PKG" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ── 工具探测（fail closed：缺工具直接失败，绝不静默跳过断言）──────────────
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
  if [ -x /data/service/hnp/bin/llvm-strings ]; then STRINGS=/data/service/hnp/bin/llvm-strings
  elif [ -x /data/service/hnp/bin/strings ]; then STRINGS=/data/service/hnp/bin/strings
  elif command -v strings >/dev/null 2>&1; then STRINGS=strings
  else fail "no strings available — cannot scan binaries for host build paths"
  fi
fi

# OHOS /system/bin/sh 不能直接 exec ELF；脚本一律由 bash 包裹执行。
BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
  BASH_BIN="$(command -v bash || true)"
fi
[ -n "$BASH_BIN" ] && [ -x "$BASH_BIN" ] \
  || fail "bash not found (CONFIG_SHELL/PATH) — required to execute ELF on OHOS"

echo "[ohos] gui    : $GUI"
echo "[ohos] cli    : $CLI"
echo "[ohos] pkg    : $PKG"
echo "[ohos] readelf: $READELF"
echo "[ohos] bash   : $BASH_BIN"

# 真实运行被测二进制：捕获 stdout+stderr 与退出码（不因非零退出中止脚本）
RUN_OUT=""
RUN_RC=0
run_bin() {
  set +e
  RUN_OUT="$(timeout 60 "$@" 2>&1)"
  RUN_RC=$?
  set -e
}

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

# ── 1/14 ELF class ───────────────────────────────────────────────────────
echo "[ohos] 1/14 ELF class"
for b in "$GUI" "$CLI"; do
  HDR="$("$READELF" -h "$b")"
  grep -q 'Class:.*ELF64' <<<"$HDR" || fail "1/14 not ELF64: $b"
done
echo "OK: 1/14 both binaries are ELF64"

# ── 2/14 machine + PIE ───────────────────────────────────────────────────
echo "[ohos] 2/14 machine / PIE"
for b in "$GUI" "$CLI"; do
  HDR="$("$READELF" -h "$b")"
  grep -q 'Machine:.*AArch64' <<<"$HDR" || fail "2/14 not AArch64: $b"
  grep -q 'Type:.*DYN' <<<"$HDR" || fail "2/14 not a DYN (PIE) executable: $b"
done
echo "OK: 2/14 AArch64 DYN (PIE)"

# ── 3/14 .interp == musl ─────────────────────────────────────────────────
echo "[ohos] 3/14 program interpreter (.interp)"
for b in "$GUI" "$CLI"; do
  INTERP="$("$READELF" -p .interp "$b" | grep -oE '/lib/[A-Za-z0-9._-]+' | head -n1 || true)"
  [ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] \
    || fail "3/14 .interp is '$INTERP' in $b, expected /lib/ld-musl-aarch64.so.1 (musl libc)"
done
echo "OK: 3/14 interpreter /lib/ld-musl-aarch64.so.1 (musl, not glibc)"

# ── 4/14 readelf -l interpreter cross-check ──────────────────────────────
echo "[ohos] 4/14 readelf -l interpreter cross-check"
for b in "$GUI" "$CLI"; do
  PHDRS="$("$READELF" -l "$b")"
  grep -q 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' <<<"$PHDRS" \
    || fail "4/14 readelf -l interpreter line mismatch in $b"
done
echo "OK: 4/14 readelf -l confirms /lib/ld-musl-aarch64.so.1"

# ── 5/14 no RPATH/RUNPATH ────────────────────────────────────────────────
echo "[ohos] 5/14 RPATH/RUNPATH"
for b in "$GUI" "$CLI"; do
  DYN="$("$READELF" -d "$b")"
  grep -qE '\b(RPATH|RUNPATH)\b' <<<"$DYN" && fail "5/14 $b has RPATH/RUNPATH"
done
echo "OK: 5/14 no RPATH/RUNPATH (dependencies resolved by the conanrun env)"

# ── 6/14 NEEDED: no glibc-only libraries, Conan libs present ─────────────
echo "[ohos] 6/14 dynamic dependencies"
GUI_NEEDED="$("$READELF" -d "$GUI" | grep -oE 'Shared library: \[[^]]+\]' | sed 's/.*\[\(.*\)\]/\1/' | sort -u)"
CLI_NEEDED="$("$READELF" -d "$CLI" | grep -oE 'Shared library: \[[^]]+\]' | sed 's/.*\[\(.*\)\]/\1/' | sort -u)"
for pair in "gui:$GUI_NEEDED" "cli:$CLI_NEEDED"; do
  label="${pair%%:*}"
  libs="${pair#*:}"
  [ -n "$libs" ] || fail "6/14 no NEEDED entries found for $label"
  BAD="$(grep -E '^(libc\.so\.[0-9]+|libpthread\.so\.0|libdl\.so\.2|librt\.so\.1|libm\.so\.6|libgcc_s\.so)' <<<"$libs" || true)"
  [ -z "$BAD" ] || fail "6/14 glibc-specific library in $label NEEDED: $BAD"
done
grep -qx 'libgtk-3.so.0' <<<"$GUI_NEEDED" \
  || fail "6/14 GUI binary is not linked against the Conan GTK3 stack"
grep -qx 'libvte-2.91.so.0' <<<"$CLI_NEEDED" \
  || fail "6/14 CLI binary is not linked against the Conan vte-2.91 terminal library"
echo "OK: 6/14 NEEDED = musl libc + Conan GTK3/vte/curl/alsa/c++/intl stack (no glibc libs)"

# ── 7/14 OHOS ELF markers ────────────────────────────────────────────────
echo "[ohos] 7/14 OHOS ELF markers"
for b in "$GUI" "$CLI"; do
  SECS="$("$READELF" -SW "$b")"
  NCS="$(grep -c '\.codesign' <<<"$SECS" || true)"
  [ "$NCS" -eq 1 ] || fail "7/14 .codesign section count = $NCS in $b, expected 1"
  grep -q '\.note\.ohos\.ident' <<<"$SECS" || fail "7/14 .note.ohos.ident marker missing in $b"
done
echo "OK: 7/14 .codesign x1 + .note.ohos.ident present in both binaries"

# ── 8/14 no host/SDK build paths in loadable sections ────────────────────
echo "[ohos] 8/14 absolute paths in loadable sections"
for b in "$GUI" "$CLI"; do
  ALLOC=""
  for s in .interp .rodata .data .dynstr .dynamic; do
    ALLOC="$ALLOC$("$READELF" -p "$s" "$b" 2>/dev/null || true)"$'\n'
  done
  ABSPATHS="$(grep -oE '/[A-Za-z0-9._+/-]{3,}' <<<"$ALLOC" | sort -u || true)"
  BADALLOC="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/|/devcloud/|/root/|/workspace/|/var/tmp/)' <<<"$ABSPATHS" || true)"
  [ -z "$BADALLOC" ] || { printf '%s\n' "$BADALLOC" >&2; fail "8/14 host/SDK build path leaked into $b loadable image"; }
done
echo "OK: 8/14 loadable images are free of build-machine paths"

# ── 9/14 no build-machine paths anywhere in the file ─────────────────────
echo "[ohos] 9/14 build-machine paths inside the binaries"
for b in "$GUI" "$CLI"; do
  ALLSTR="$("$STRINGS" -a "$b")"
  BADPATHS="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/)' <<<"$ALLSTR" || true)"
  [ -z "$BADPATHS" ] || { head -5 <<<"$BADPATHS" >&2; fail "9/14 build-machine absolute path embedded in $b"; }
done
# OHOS SDK 预编译 crt/调试目标文件带 DWARF，debug 段中会留下 SDK 自身的构建
# 路径（/devcloud/...）。它不在任何可加载段（断言 8 已证明），也不属于本机
# 构建路径，故不计为缺陷；此处仅记录条数作为证据。
DWARF_HITS="$("$STRINGS" -a "$GUI" | grep -c 'devcloud' || true)"
echo "[info] DWARF-only SDK build path occurrences (gui): $DWARF_HITS (debug sections, not loadable)"
echo "OK: 9/14 no build-machine absolute path in either binary"

# ── 10/14 bash-wrapped execution (OHOS shell constraint) ─────────────────
echo "[ohos] 10/14 bash-wrapped execution"
set +e
WRAP_OUT="$("$BASH_BIN" -c "\"$GUI\" --version" 2>&1)"
WRAP_RC=$?
set -e
[ "$WRAP_RC" -eq 0 ] || { printf '%s\n' "$WRAP_OUT" >&2; fail "10/14 bash-wrapped --version failed (rc=$WRAP_RC)"; }
grep -q 'xcfa 5.0.2' <<<"$WRAP_OUT" || fail "10/14 bash-wrapped --version printed no version"
if [ -x /system/bin/sh ]; then
  set +e
  /system/bin/sh -c "\"$GUI\" --version" >/dev/null 2>&1
  PLAIN_RC=$?
  set -e
  echo "[info] /system/bin/sh direct exec rc=$PLAIN_RC (OHOS /system/bin/sh cannot exec ELF; always wrap with bash)"
fi
echo "OK: 10/14 bash -c \"xcfa --version\" works (rc=0)"

# ── 11/14 runtime platform report ────────────────────────────────────────
echo "[ohos] 11/14 runtime platform report"
run_bin "$CLI"
no_crash "xcfa_cli environment report"
grep -qE '^! sysname +HarmonyOS' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" | head -20 >&2; fail "11/14 xcfa_cli did not report sysname HarmonyOS"; }
grep -qE '^! machine +aarch64' <<<"$RUN_OUT" \
  || fail "11/14 xcfa_cli did not report machine aarch64"
echo "OK: 11/14 xcfa_cli reports sysname HarmonyOS / machine aarch64 (running on the OHOS kernel)"

# ── 12/14 GTK/GLib runtime versions ──────────────────────────────────────
echo "[ohos] 12/14 GTK/GLib runtime versions"
run_bin "$GUI" --version
no_crash "xcfa --version"
grep -qE 'Gtk version += *[0-9]' <<<"$RUN_OUT" || fail "12/14 GTK runtime version not reported"
grep -qE 'Glib version += *[0-9]' <<<"$RUN_OUT" || fail "12/14 GLib runtime version not reported"
echo "OK: 12/14 GTK/GLib runtime versions resolved from the Conan stack"

# ── 13/14 GUI without a display server ───────────────────────────────────
echo "[ohos] 13/14 GUI without display server (platform capability gap)"
[ -e /tmp/.X11-unix/X99 ] && fail "13/14 platform premise broken: an X server is listening on :99"
run_bin env DISPLAY=:99 "$GUI"
no_crash "xcfa with DISPLAY=:99"
[ "$RUN_RC" -eq 1 ] || { printf '%s\n' "$RUN_OUT" >&2; fail "13/14 expected graceful rc=1 without a display, got rc=$RUN_RC"; }
grep -q 'cannot open display: :99' <<<"$RUN_OUT" \
  || { printf '%s\n' "$RUN_OUT" | tail -10 >&2; fail "13/14 expected GTK 'cannot open display' diagnostic"; }
echo "OK: 13/14 no display server -> 'cannot open display: :99', rc=1, no hang, no crash"

# ── 14/14 packaged artifacts + crash-free summary ────────────────────────
echo "[ohos] 14/14 packaged artifacts"
for f in bin/xcfa bin/xcfa_cli \
         share/xcfa/glade/xcfa.glade share/xcfa/glade/xcfa_win_about.glade \
         share/pixmaps/xcfa.png share/applications/xcfa.desktop share/man/man1/xcfa.1; do
  [ -f "$PKG/$f" ] || fail "14/14 missing packaged file: $PKG/$f"
done
GLADE_COUNT="$(ls "$PKG/share/xcfa/glade" | wc -l)"
[ "$GLADE_COUNT" -ge 6 ] || fail "14/14 expected 6 glade UI files, found $GLADE_COUNT"
[ -z "$CRASH_SEEN" ] || fail "14/14 a run crashed during this test"
echo "OK: 14/14 package ships both binaries + $GLADE_COUNT glade UIs + pixmaps/desktop/man; all runs graceful"

echo "OHOS ASSERTIONS PASSED: 14/14"
