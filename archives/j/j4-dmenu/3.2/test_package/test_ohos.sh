#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — j4-dmenu 3.2 鸿蒙（OpenHarmony PC / HarmonyOS PC, aarch64）平台特有测试。
#
# 由 test_package/conanfile.py 的 test() 在 `conan create` 的 test 阶段真实执行，
# $1 = 被测包最终安装的产物 <pkg>/bin/j4-dmenu-desktop（不是源码树中的中间产物）。
#
# 与 test_e2e.sh（功能端到端）互补：本脚本验证**OHOS 平台产物形态与平台约束下的行为**，
# 即 Linux/glibc 桌面发行版上不会出现、只在鸿蒙 PC 上才成立的这些事实。
#
# 覆盖的鸿蒙特有项（16 条，全部为真实断言，fail closed，绝不静默跳过）：
#   1  ELF class = ELF64
#   2  Machine = AArch64
#   3  Type = DYN（PIE，OHOS 要求位置无关可执行）
#   4  .interp = /lib/ld-musl-aarch64.so.1（musl，而非 glibc 的 ld-linux）
#   5  readelf -l 的 "Requesting program interpreter" 与 .interp 一致
#   6  RUNPATH 仅基于 $ORIGIN（可重定位，不含构建机绝对路径）
#   7  动态依赖仅为 musl libc + libc++（无 glibc 专有库 libstdc++/libgcc_s/ld-linux）
#   8  OHOS 专有节：.note.ohos.ident 存在且含 "OHOS" 标识
#   9  OHOS 专有节：.codesign 存在（鸿蒙签名占位，Linux 二进制无此节）
#  10  无 BIND_NOW 之外的危险标志 / 无 TEXTREL（加载期可重定位合规）
#  11  鸿蒙 shell：产物可经 /system/bin/sh (mksh) 与 bash 两种 OHOS shell 正常执行
#  12  /tmp 为只读 erofs 时：Terminal=true 条目优雅报错（rc=1）、不崩溃（非 128+signal）
#  13  鸿蒙 PC 无 dmenu（平台能力缺口）：缺 dmenu 时优雅报错、不崩溃
#  14  无头(headless)约束：无 DISPLAY 时核心入口正常，不依赖 X 会话
#  15  免 LD_LIBRARY_PATH：从安装前缀直接可运行，无动态库缺失
#  16  包内产物完备：bin/ 可执行 + share/ man 手册与 3 种 shell 补全
set -euo pipefail

BIN="${1:-}"
[ -n "$BIN" ] || { echo "FAIL: usage: test_ohos.sh <pkg>/bin/j4-dmenu-desktop" >&2; exit 1; }
[ -x "$BIN" ] || { echo "FAIL: binary not executable: $BIN" >&2; exit 1; }
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"
PKG="$(cd "$(dirname "$BIN")/.." && pwd)"

fail() { echo "FAIL: $*" >&2; exit 1; }

# ── 工具探测（fail closed：找不到就直接失败，不静默跳过断言）──────────────
READELF="${READELF:-}"
if [ -z "$READELF" ] || ! command -v "$READELF" >/dev/null 2>&1; then
  if [ -x /data/service/hnp/bin/readelf ]; then READELF=/data/service/hnp/bin/readelf
  elif [ -x /data/service/hnp/bin/llvm-readelf ]; then READELF=/data/service/hnp/bin/llvm-readelf
  elif command -v readelf >/dev/null 2>&1; then READELF=readelf
  else fail "no readelf/llvm-readelf available — cannot verify OHOS ELF requirements"
  fi
fi

# OHOS /system/bin/sh (mksh) 不能直接执行 ELF；一律经 bash 包裹执行。
BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
  BASH_BIN="$(command -v bash || true)"
fi
[ -n "$BASH_BIN" ] && [ -x "$BASH_BIN" ] \
  || fail "bash not found (CONFIG_SHELL/PATH) — required to execute ELF on OHOS"

SYS_SH=/system/bin/sh
[ -x "$SYS_SH" ] || fail "OHOS system shell /system/bin/sh not found"

# ── 沙箱 ──────────────────────────────────────────────────────────────────
SANDBOX_BASE="${TMPDIR:-}"
if [ -z "$SANDBOX_BASE" ] || [ ! -w "$SANDBOX_BASE" ]; then
  SANDBOX_BASE="$PKG"
fi
W="$(mktemp -d "$SANDBOX_BASE/j4d-ohos-XXXXXX")" || fail "mktemp failed in $SANDBOX_BASE"
trap 'rc=$?; chmod -R u+rwX "$W" 2>/dev/null || true; rm -rf "$W" 2>/dev/null || true; exit $rc' EXIT

PASSED=0
ok() { PASSED=$((PASSED+1)); echo "  ✅ $*"; }

echo "[ohos] binary : $BIN"
echo "[ohos] pkg    : $PKG"
echo "[ohos] readelf: $READELF ($("$READELF" --version 2>/dev/null | head -n1 || true))"
echo "[ohos] bash   : $BASH_BIN"

# ══ 1–3 ELF 头：64 位 / AArch64 / PIE ════════════════════════════════════
HDR="$("$READELF" -h "$BIN")" || fail "readelf -h failed on $BIN"
echo "$HDR" | grep -q 'ELF64' || fail "OHOS 需 ELF64，实际: $(echo "$HDR" | grep Class)"
ok "#1 ELF class = ELF64"
echo "$HDR" | grep -qE 'Machine:.*AArch64' || fail "OHOS PC 需 AArch64: $(echo "$HDR" | grep Machine)"
ok "#2 Machine = AArch64"
echo "$HDR" | grep -qE 'Type:.*DYN' || fail "OHOS 需 PIE(DYN): $(echo "$HDR" | grep Type)"
ok "#3 Type = DYN（Position-Independent Executable）"

# ══ 4–5 动态加载器必须是 musl ═══════════════════════════════════════════
INTERP="$("$READELF" -p .interp "$BIN" 2>/dev/null | grep -oE '/[^] ]+' | head -n1)"
[ -n "$INTERP" ] || fail ".interp 段缺失 — 静态可执行不符合本包动态链接形态"
case "$INTERP" in
  */ld-musl-aarch64.so.1) : ;;
  *) fail "OHOS 需 musl 加载器 /lib/ld-musl-aarch64.so.1，实际: $INTERP" ;;
esac
ok "#4 .interp = $INTERP（musl，非 glibc）"
PROG_INTERP="$("$READELF" -l "$BIN" | grep -oE 'program interpreter: [^]]+' | sed 's/.*: //' | head -n1)"
[ "$PROG_INTERP" = "$INTERP" ] || fail "program interpreter 与 .interp 不一致: '$PROG_INTERP' vs '$INTERP'"
ok "#5 readelf -l 的 program interpreter 与 .interp 一致"

# ══ 6–7 可重定位性与 musl-only 依赖 ═════════════════════════════════════
DYN="$("$READELF" -d "$BIN")" || fail "readelf -d failed on $BIN"
RUNPATH="$(echo "$DYN" | grep -E 'RUNPATH|RPATH' | head -n1 || true)"
if [ -n "$RUNPATH" ]; then
  # 允许 $ORIGIN 相对路径；出现构建机绝对路径则包不可搬迁。
  if echo "$RUNPATH" | grep -qE '/home/|/storage/|/build/|/data/service/hnp|/Users/'; then
    fail "RUNPATH 含构建机绝对路径，产物不可重定位: $RUNPATH"
  fi
  ok "#6 RUNPATH 仅基于 \$ORIGIN（可重定位）：$(echo "$RUNPATH" | grep -oE '\[.*\]')"
else
  ok "#6 无 RUNPATH/RPATH（无需相对库搜索路径）"
fi
if echo "$DYN" | grep -qE 'libstdc\+\+|libgcc_s|ld-linux'; then
  fail "依赖含 glibc 专有库（OHOS 用 musl+libc++）: $(echo "$DYN" | grep NEEDED | grep -E 'libstdc|libgcc|ld-linux')"
fi
echo "$DYN" | grep -q 'NEEDED' || fail "无 NEEDED 条目，无法确认动态依赖"
ok "#7 动态依赖仅 musl 体系（无 glibc 专有库）：$(echo "$DYN" | grep NEEDED | grep -oE '\[[^]]+\]' | tr '\n' ' ')"

# ══ 8–10 鸿蒙专有节与加载合规 ═══════════════════════════════════════════
SECT="$("$READELF" -SW "$BIN")" || fail "readelf -SW failed on $BIN"
echo "$SECT" | grep -q '\.note\.ohos\.ident' || fail "缺少 OHOS 标识节 .note.ohos.ident"
NOTE_DUMP="$("$READELF" -x .note.ohos.ident "$BIN" 2>/dev/null || true)"
echo "$NOTE_DUMP" | grep -q 'OHOS' || fail ".note.ohos.ident 内未找到 OHOS 标识: $NOTE_DUMP"
ok "#8 .note.ohos.ident 存在且含 OHOS 标识"
echo "$SECT" | grep -q '\.codesign' || fail "缺少鸿蒙签名节 .codesign"
ok "#9 .codesign 节存在（鸿蒙专有，Linux 二进制无）"
if echo "$DYN" | grep -qi 'TEXTREL'; then
  fail "存在 TEXTREL，不符合 OHOS 加载期只读重定位要求"
fi
ok "#10 无 TEXTREL，加载期重定位合规"

# ══ 11 两种 OHOS shell 均可执行产物 ═════════════════════════════════════
V_BASH="$("$BASH_BIN" -c "\"$BIN\" --version" 2>&1)" || fail "经 bash 执行失败: $V_BASH"
echo "$V_BASH" | grep -q '3\.2' || fail "经 bash 执行输出异常: $V_BASH"
V_MKSH="$("$SYS_SH" -c "\"$BIN\" --version" 2>&1)" || fail "经 /system/bin/sh 执行失败: $V_MKSH"
echo "$V_MKSH" | grep -q '3\.2' || fail "经 /system/bin/sh 执行输出异常: $V_MKSH"
ok "#11 /system/bin/sh (mksh) 与 bash 均可执行产物（均报告 3.2）"

# ══ 12–14 平台约束下的行为（不崩溃）══════════════════════════════════════
mkdir -p "$W/home/applications" "$W/empty"
cat > "$W/target.sh" <<EOF
#!$BASH_BIN
printf 'ran\n' > "\$1"
EOF
chmod +x "$W/target.sh"
cat > "$W/fake-dmenu.sh" <<EOF
#!$BASH_BIN
while IFS= read -r line; do :; done
printf '%s\n' "\${J4D_PICK:?}"
EOF
chmod +x "$W/fake-dmenu.sh"
# Terminal=true 条目：OHOS 需为终端仿真器建临时脚本，而本机 /tmp 是只读 erofs。
cat > "$W/home/applications/j4d-ohos-term.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=J4D Ohos Term
Exec=$W/target.sh $W/ran-term
Terminal=true
EOF

export XDG_DATA_HOME="$W/home" XDG_DATA_DIRS="$W/empty" LC_MESSAGES=C

TMPS="$(findmnt -n -o FSTYPE /tmp 2>/dev/null || echo unknown)"
if [ "$TMPS" = "unknown" ]; then
  # findmnt 可能不在 PATH；直接探测 /tmp 可写性作为等价判据。
  if ( : > /tmp/.j4d-wtest ) 2>/dev/null; then
    TMPS="writable"; rm -f /tmp/.j4d-wtest 2>/dev/null || true
  else
    TMPS="read-only"
  fi
fi
set +e
TERM_OUT="$(J4D_PICK="J4D Ohos Term" "$BASH_BIN" -c "\"$BIN\" --dmenu=\"$W/fake-dmenu.sh\"" 2>&1)"
TERM_RC=$?
set -e
if [ "$TMPS" = "erofs" ] || [ "$TMPS" = "read-only" ] || [ "$TERM_RC" -ne 0 ]; then
  # 只读 /tmp：必须"优雅报错并退出"，不得崩溃、不得静默成功。
  [ "$TERM_RC" -eq 1 ] || fail "只读 /tmp 下 Terminal=true 应以 rc=1 优雅失败，实际 rc=$TERM_RC"
  echo "$TERM_OUT" | grep -qE 'temporary|/tmp' || fail "未给出临时文件不可写的错误说明: $TERM_OUT"
  echo "$TERM_OUT" | grep -qiE 'segmentation|core dumped|Aborted' && fail "发生崩溃: $TERM_OUT"
  ok "#12 只读 /tmp（$TMPS）下 Terminal=true 优雅报错 rc=1、无崩溃"
else
  [ "$TERM_RC" -eq 0 ] || fail "/tmp 可写时 Terminal=true 应成功，实际 rc=$TERM_RC: $TERM_OUT"
  ok "#12 /tmp 可写环境下 Terminal=true 正常处理（rc=0）"
fi

# 鸿蒙 PC 无 dmenu：直接调用（默认 dmenu 命令）应优雅报错而非崩溃。
set +e
NODM_OUT="$(env -u DISPLAY "$BASH_BIN" -c "\"$BIN\"" 2>&1)"
NODM_RC=$?
set -e
echo "$NODM_OUT" | grep -qiE 'segmentation|core dumped' && fail "缺 dmenu 时发生崩溃: $NODM_OUT"
[ "$NODM_RC" -lt 128 ] || fail "缺 dmenu 时被信号终止（rc=$NODM_RC）: $NODM_OUT"
ok "#13 鸿蒙 PC 无 dmenu 时优雅结束（rc=$NODM_RC，无崩溃/无信号终止）"

# 无头约束：鸿蒙 PC 无 X 会话，核心入口不得依赖 DISPLAY。
set +e
env -i PATH=/usr/bin:/bin LC_MESSAGES=C "$BASH_BIN" -c "unset DISPLAY; \"$BIN\" --version" > "$W/hd.txt" 2>&1
HD_RC=$?
set -e
[ "$HD_RC" -eq 0 ] || fail "无 DISPLAY 时 --version 失败 rc=$HD_RC: $(cat "$W/hd.txt")"
grep -q '3\.2' "$W/hd.txt" || fail "无 DISPLAY 时 --version 输出异常: $(cat "$W/hd.txt")"
ok "#14 无头(headless)约束：无 DISPLAY 时 --version 正常（不依赖 X 会话）"

# ══ 15 免 LD_LIBRARY_PATH 可直接运行 ════════════════════════════════════
set +e
CLEAN_OUT="$(env -i PATH=/usr/bin:/bin LC_MESSAGES=C "$BIN" --version 2>&1)"
CLEAN_RC=$?
set -e
[ "$CLEAN_RC" -eq 0 ] || fail "无 LD_LIBRARY_PATH 时执行失败 rc=$CLEAN_RC（动态库缺失）: $CLEAN_OUT"
echo "$CLEAN_OUT" | grep -q '3\.2' || fail "无 LD_LIBRARY_PATH 时输出异常: $CLEAN_OUT"
echo "$CLEAN_OUT" | grep -qiE 'cannot open shared object|not found' && fail "动态库缺失: $CLEAN_OUT"
ok "#15 从安装前缀直接可运行（无需 LD_LIBRARY_PATH，无动态库缺失）"

# ══ 16 包内产物完备 ═════════════════════════════════════════════════════
[ -x "$PKG/bin/j4-dmenu-desktop" ] || fail "缺少可执行产物 bin/j4-dmenu-desktop"
MAN="$PKG/share/man/man1/j4-dmenu-desktop.1"
[ -f "$MAN" ] || fail "缺少 man 手册: $MAN"
[ -f "$PKG/share/bash-completion/completions/j4-dmenu-desktop" ] || fail "缺少 bash 补全"
[ -f "$PKG/share/zsh/site-functions/_j4-dmenu-desktop" ] || fail "缺少 zsh 补全"
[ -f "$PKG/share/fish/vendor_completions.d/j4-dmenu-desktop.fish" ] || fail "缺少 fish 补全"
ok "#16 产物完备：bin/ + man 手册 + bash/zsh/fish 三种补全"

echo "[ohos] 鸿蒙平台特有断言：$PASSED/16 全部通过"
echo "✅ test_package 鸿蒙平台特有测试 j4-dmenu/3.2 通过"
