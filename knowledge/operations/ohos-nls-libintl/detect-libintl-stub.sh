#!/usr/bin/env bash
#==============================================================================
# detect-libintl-stub.sh — OHOS NLS/gettext(libintl) 适配检测器
#
# 背景：glibc 把 gettext 的 libintl 并进 libc，导致「用了 dgettext() 却没
#       #include <libintl.h>」这类历史写法在 GNU 平台能编过；OHOS(musl) 的
#       sysroot 里 <libintl.h> 是空壳且不提供 libintl，同一源码会编译/链接失败。
#
# 本脚本做两件事：
#   A. 环境探针：用目标平台 clang 验证 <libintl.h> 是否可用、-lintl 是否存在
#      （默认 aarch64-linux-ohos；可用 --clang/--sysroot 覆盖）
#   B. 源码静态扫描：找出「使用 gettext 家族函数但未包含 <libintl.h>」的位置，
#      给出文件:行与处理建议
#
# 退出码：0 = 未发现问题；10 = 发现问题；2 = 用法/环境错误
#
# 约束：不在脚本里写死某台机器的绝对路径（一律经环境变量或 --clang/--sysroot
#       覆盖，缺省只在 PATH 与 $OHOS_SDK/$HOME 下探测）；日志写入 ${TMPDIR:-$HOME/tmp}
#       而非直接管道给 head（避免 SIGPIPE 与"只看到前几行"）。
#
# 用法：
#   detect-libintl-stub.sh [--src DIR]... [--json] [--no-scan] [--no-probe]
#                          [--clang PATH] [--sysroot DIR] [--quiet] [--log FILE]
#   默认：--src 当前目录，probe + scan 都做
#==============================================================================
set -u

log_line() { printf '%s\n' "$*" >>"$OHOS_LOGFILE"; }
say()      { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; log_line "$*"; }
say_err()  { printf '%s\n' "$*" >&2; log_line "$*"; }

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

SRCS=""; JSON=0; DO_SCAN=1; DO_PROBE=1; QUIET=0
CLANG_OPT=""; SYSROOT_OPT=""; LOG_OPT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --src)      [ $# -ge 2 ] || { say_err "--src 需要目录参数"; exit 2; }; SRCS="$SRCS $2"; shift 2 ;;
    --json)     JSON=1; shift ;;
    --no-scan)  DO_SCAN=0; shift ;;
    --no-probe) DO_PROBE=0; shift ;;
    --clang)    [ $# -ge 2 ] || { say_err "--clang 需要路径参数"; exit 2; }; CLANG_OPT="$2"; shift 2 ;;
    --sysroot)  [ $# -ge 2 ] || { say_err "--sysroot 需要目录参数"; exit 2; }; SYSROOT_OPT="$2"; shift 2 ;;
    --log)      [ $# -ge 2 ] || { say_err "--log 需要文件参数"; exit 2; }; LOG_OPT="$2"; shift 2 ;;
    --quiet)    QUIET=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *)          say_err "未知参数: $1"; usage >&2; exit 2 ;;
  esac
done
[ -n "$SRCS" ] || SRCS=" ."

TMPBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPBASE" 2>/dev/null || { say_err "无法创建临时目录 $TMPBASE"; exit 2; }
if [ -n "$LOG_OPT" ]; then OHOS_LOGFILE="$LOG_OPT"; else OHOS_LOGFILE="$TMPBASE/ohos-libintl-detect-$(date +%Y%m%d-%H%M%S).log"; fi
: >"$OHOS_LOGFILE" 2>/dev/null || { say_err "无法写日志 $OHOS_LOGFILE"; exit 2; }

log_line "=== detect-libintl-stub.sh $(date '+%F %T') ==="
log_line "src:${SRCS}"
log_line "tmp:${TMPBASE}"

#------------------------------------------------------------------------------
# 1. 工具链探测（不写死绝对路径：env > --clang > PATH > 常见 SDK 相对位置）
#------------------------------------------------------------------------------
find_clang() {
  if [ -n "$CLANG_OPT" ]; then printf '%s' "$CLANG_OPT"; return; fi
  if [ -n "${OHOS_CLANG:-}" ]; then printf '%s' "$OHOS_CLANG"; return; fi
  if [ -n "${CC:-}" ] && command -v "${CC%% *}" >/dev/null 2>&1; then printf '%s' "${CC%% *}"; return; fi
  local c
  for c in clang++ clang; do
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return; fi
  done
  # 常见 OHOS/本地 SDK 相对位置（可由 OHOS_SDK 覆盖；找不到不影响静态扫描）
  local root="${OHOS_SDK:-}"
  local cand=""
  [ -n "$root" ] && cand="$cand $root/native/llvm/bin/clang $root/native/llvm/bin/clang++"
  cand="$cand $HOME/.ohos-sdk/native/llvm/bin/clang $HOME/ohos-sdk/native/llvm/bin/clang"
  cand="$cand ${OHOS_SDK_ROOT:-}/native/llvm/bin/clang"
  for c in $cand; do
    [ -n "$c" ] && [ -x "$c" ] && { printf '%s' "$c"; return; }
  done
  printf ''
}

find_sysroot() {
  if [ -n "$SYSROOT_OPT" ]; then printf '%s' "$SYSROOT_OPT"; return; fi
  if [ -n "${OHOS_SYSROOT:-}" ]; then printf '%s' "$OHOS_SYSROOT"; return; fi
  local cc="$1"
  [ -n "$cc" ] || { printf ''; return; }
  local d; d="$(dirname "$(readlink -f "$cc" 2>/dev/null || printf '%s' "$cc")")"
  local c
  for c in "$d/../sysroot" "$d/../../sysroot" "$d/../usr"; do
    [ -f "$c/usr/include/libintl.h" ] || [ -f "$c/include/libintl.h" ] || [ -d "$c" ] && [ -n "$(ls "$c" 2>/dev/null)" ] && { printf '%s' "$(cd "$c" && pwd)"; return; }
  done
  printf ''
}

TARGET_TRIPLE="${OHOS_TARGET:-aarch64-linux-ohos}"
CLANG="$(find_clang)"
SYSROOT="$(find_sysroot "$CLANG")"

log_line "clang:${CLANG:-<none>} sysroot:${SYSROOT:-<none>} target:${TARGET_TRIPLE}"

#------------------------------------------------------------------------------
# 2. 环境探针：目标平台 <libintl.h> / -lintl 是否可用
#    结论写入 HEADER_OK / LINKINTL_OK / IMPLICIT_OK，供扫描阶段定级
#------------------------------------------------------------------------------
PROBE_STATE="skipped"
HEADER_OK=0; LINKINTL_OK=0; IMPLICIT_OK=0

run_probe() {
  [ "$DO_PROBE" = 1 ] || return 0
  [ -n "$CLANG" ] || { PROBE_STATE="skipped(no-clang)"; say_err "[probe] 未找到 clang，跳过环境探针（可用 --clang 指定）"; return 0; }

  local wd="$TMPBASE/ohos-libintl-probe.$$"
  mkdir -p "$wd" || { PROBE_STATE="error"; return 0; }
  local flags="--target=$TARGET_TRIPLE"
  [ -n "$SYSROOT" ] && flags="$flags --sysroot=$SYSROOT"

  printf '#include <libintl.h>\nint main(void){ (void)dgettext("ohos","probe"); return 0; }\n' >"$wd/with_header.c"
  printf '/* 模拟 glibc 隐式声明写法：不包含 libintl.h */\nint main(void){ (void)dgettext("ohos","probe"); return 0; }\n' >"$wd/implicit.c"

  log_line "--- probe: include <libintl.h> ($CLANG $flags) ---"
  if $CLANG $flags -c "$wd/with_header.c" -o "$wd/with_header.o" >>"$OHOS_LOGFILE" 2>&1; then
    HEADER_OK=1
  else
    HEADER_OK=0
  fi
  log_line "HEADER_OK=$HEADER_OK"

  if [ "$HEADER_OK" = 1 ]; then
    log_line "--- probe: link -lintl ---"
    if $CLANG $flags "$wd/with_header.c" -lintl -o "$wd/with_header.bin" >>"$OHOS_LOGFILE" 2>&1; then
      LINKINTL_OK=1
    else
      LINKINTL_OK=0
    fi
  else
    log_line "--- probe: link -lintl (skipped, header 不可用) ---"
    LINKINTL_OK=0
  fi
  log_line "LINKINTL_OK=$LINKINTL_OK"

  log_line "--- probe: 隐式声明（不含 libintl.h）---"
  if $CLANG $flags -c "$wd/implicit.c" -o "$wd/implicit.o" >>"$OHOS_LOGFILE" 2>&1; then
    IMPLICIT_OK=1     # glibc 风格：隐式声明能过 → OHOS 上会炸
  else
    IMPLICIT_OK=0
  fi
  log_line "IMPLICIT_OK=$IMPLICIT_OK"

  rm -rf "$wd" 2>/dev/null
  PROBE_STATE="done"
}

#------------------------------------------------------------------------------
# 3. 源码静态扫描：gettext 家族调用 vs <libintl.h> 覆盖情况
#------------------------------------------------------------------------------
NL_HEADER_RE='^[[:space:]]*#[[:space:]]*include[[:space:]]*[<"]libintl\.h[>"]'
INCLUDE_RE='^[[:space:]]*#[[:space:]]*include[[:space:]]*"([^"]+)"'
CALL_RE='(^|[^A-Za-z0-9_])(dgettext|dcgettext|dngettext|ngettext|gettext|bindtextdomain|textdomain|bind_textdomain_codeset)[[:space:]]*\('
# 提供者特征：类型标记 + 空白 + 符号 + '(' —— 即"声明/定义 gettext 家族"而非调用它
# （如 inline char *dgettext(...){...} 或 char *dgettext(const char *, const char *);）
# 这类文件是 libintl 的提供方（兜底头/自实现），不应被判为需要包含 libintl.h 的调用方
DEF_RE='(^|[^A-Za-z0-9_.>=-])[A-Za-z_][A-Za-z0-9_:<>]*[[:space:]]*\*?[[:space:]]+(dgettext|dcgettext|dngettext|ngettext|gettext|bindtextdomain|textdomain|bind_textdomain_codeset)[[:space:]]*\('

FINDINGS_FILE="$TMPBASE/ohos-libintl-findings.$$"
: >"$FINDINGS_FILE"
FILES_SCANNED=0; FILES_WITH_CALLS=0; FILES_COVERED=0; N_BLOCKER=0; N_WARN=0; N_INFO=0

collect_files() {
  local d
  for d in $SRCS; do
    [ -d "$d" ] || continue
    find "$d" -type f \
      \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \
         -o -name '*.h' -o -name '*.hh' -o -name '*.hpp' -o -name '*.hxx' \) \
      -not -path '*/.git/*' -not -path '*/build/*' -not -path '*/_build/*' \
      -not -path '*/.conan2/*' -not -path '*/node_modules/*' 2>/dev/null
  done
}

# 本地头一跳解析的候选根：每个 --src 目录本身及其 include/ 子目录
SRC_ROOTS=""
collect_roots() {
  local d
  for d in $SRCS; do
    [ -d "$d" ] || continue
    case " $SRC_ROOTS " in *" $d "*) ;; *) SRC_ROOTS="$SRC_ROOTS $d" ;; esac
    [ -d "$d/include" ] && case " $SRC_ROOTS " in *" $d/include "*) ;; *) SRC_ROOTS="$SRC_ROOTS $d/include" ;; esac
  done
}
collect_roots

# 该翻译单元是否（自身或经本地头一跳）包含 libintl.h
# 候选顺序：自身 → 同目录 → 各 src 根 → 各 src 根的 include/
file_covers_libintl() {
  local f="$1" inc p dir root
  grep -qE "$NL_HEADER_RE" "$f" 2>/dev/null && return 0
  dir="$(dirname "$f")"
  while IFS= read -r inc; do
    [ -n "$inc" ] || continue
    for root in "$dir" $SRC_ROOTS; do
      p="$root/$inc"
      [ -f "$p" ] || continue
      grep -qE "$NL_HEADER_RE" "$p" 2>/dev/null && return 0
    done
  done < <(sed -nE "s/$INCLUDE_RE/\1/p" "$f" 2>/dev/null)
  return 1
}

scan_files() {
  local f hits first_line first_sym n covers sev reason
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    FILES_SCANNED=$((FILES_SCANNED + 1))
    # 提供者文件不算调用方：libintl.h 本体，或自身声明/定义了 gettext 家族
    case "$(basename "$f")" in
      libintl.h|libintl.hpp) log_line "skip provider header $f"; continue ;;
    esac
    if grep -qE "$DEF_RE" "$f" 2>/dev/null; then
      log_line "skip provider implementation $f"
      continue
    fi
    hits="$(grep -nE "$CALL_RE" "$f" 2>/dev/null | grep -vE '^[0-9]+:[[:space:]]*(//|\*|/\*)')"
    [ -n "$hits" ] || continue
    FILES_WITH_CALLS=$((FILES_WITH_CALLS + 1))

    covers=0; file_covers_libintl "$f" && covers=1
    [ "$covers" = 1 ] && FILES_COVERED=$((FILES_COVERED + 1))

    first_line="$(printf '%s\n' "$hits" | sed -nE '1s/^([0-9]+):.*/\1/p')"
    first_sym="$(printf '%s\n' "$hits" | sed -nE '1s/.*[^A-Za-z0-9_]([a-z_]+)\(.*/\1/p')"
    [ -n "$first_sym" ] || first_sym="gettext"
    n="$(printf '%s\n' "$hits" | wc -l | tr -d ' ')"

    if [ "$covers" = 1 ]; then
      if [ "$PROBE_STATE" = "done" ] && [ "$HEADER_OK" = 0 ]; then
        sev="blocker"; reason="包含 libintl.h，但目标平台该头不可用（空壳/缺失）"
      else
        sev="info";    reason="已包含 libintl.h；仍须确认依赖 gettext 并提供 libintl"
      fi
    elif [ "$PROBE_STATE" = "done" ] && [ "$HEADER_OK" = 0 ]; then
      sev="blocker"; reason="调用 $first_sym 未包含 libintl.h，目标平台无可用 libintl.h"
    else
      sev="warn";    reason="调用 $first_sym 未包含 libintl.h（GNU 隐式声明可过，OHOS 不可移植）"
    fi

    case "$sev" in
      blocker) N_BLOCKER=$((N_BLOCKER + 1)) ;;
      warn)    N_WARN=$((N_WARN + 1)) ;;
      *)       N_INFO=$((N_INFO + 1)) ;;
    esac
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$f" "$first_line" "$first_sym" "$sev" "$n" "$reason" >>"$FINDINGS_FILE"
    log_line "finding $f:$first_line sym=$first_sym sev=$sev hits=$n"
  done < <(collect_files | sort -u)
}

#------------------------------------------------------------------------------
# 4. 报告与退出码
#------------------------------------------------------------------------------
emit_strategies() {
  say ""
  say "[策略] 三选一（推荐 ①；对应知识条目 schroot-1.6.13-ohos-libintl-stub）"
  say " ① 补 #include <libintl.h>：加在调用 TU 或它的（包装）头里；配方 requires=\"gettext/<ver>\"，"
  say "    链接期带 -lintl（gettext 包提供 libintl.h + libintl.so）。有封装头的库优先改封装头，调用点不动。"
  say " ② 关闭 NLS：上游若有开关（--disable-nls / -DENABLE_NLS=OFF / 探测 HAVE_LIBINTL_H），配方 generate() 里显式关掉；"
  say "    代价=丢失本地化。"
  say " ③ 自建 i18n 封装：无本地化需求时把 gettext 家族定义成恒等宏，避免依赖 glibc 隐式符号。"
}

report_text() {
  say "[probe] target=$TARGET_TRIPLE"
  if [ "$PROBE_STATE" = "done" ]; then
    say "        clang=$CLANG"
    say "        <libintl.h> 可编译=$HEADER_OK   -lintl 可链接=$LINKINTL_OK   隐式声明可编译=$IMPLICIT_OK"
    [ "$HEADER_OK" = 0 ] && say "        => 目标平台无可用 libintl.h：未包含该头的 gettext 调用必然失败"
  else
    say "        探针状态=$PROBE_STATE（静态扫描结论按 warn 定级）"
  fi
  say "[scan] 扫描文件=$FILES_SCANNED 含 gettext 调用=$FILES_WITH_CALLS 已含 libintl.h=$FILES_COVERED"
  if [ -s "$FINDINGS_FILE" ]; then
    say ""
    say "文件:行 | 符号 | 级别 | 同文件调用数 | 说明"
    while IFS="$(printf '\t')" read -r f ln sym sev n reason; do
      say "  $f:$ln | $sym | $sev | $n | $reason"
    done <"$FINDINGS_FILE"
  else
    say "  （无 gettext 家族调用命中）"
  fi
  [ $((N_BLOCKER + N_WARN)) -gt 0 ] && emit_strategies
  say ""
  say "[summary] blocker=$N_BLOCKER warn=$N_WARN info=$N_INFO"
  say "[log] $OHOS_LOGFILE"
}

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

report_json() {
  local first=1
  printf '{"script":"detect-libintl-stub.sh","target":"%s","clang":"%s","sysroot":"%s",' \
    "$(json_escape "$TARGET_TRIPLE")" "$(json_escape "${CLANG:-}")" "$(json_escape "${SYSROOT:-}")"
  printf '"probe":{"state":"%s","header_ok":%s,"libintl_ok":%s,"implicit_ok":%s},' \
    "$PROBE_STATE" "$([ "$HEADER_OK" = 1 ] && printf true || printf false)" \
    "$([ "$LINKINTL_OK" = 1 ] && printf true || printf false)" \
    "$([ "$IMPLICIT_OK" = 1 ] && printf true || printf false)"
  printf '"scan":{"files":%s,"files_with_calls":%s,"files_covered":%s},' \
    "$FILES_SCANNED" "$FILES_WITH_CALLS" "$FILES_COVERED"
  printf '"findings":['
  if [ -s "$FINDINGS_FILE" ]; then
    while IFS="$(printf '\t')" read -r f ln sym sev n reason; do
      [ "$first" = 1 ] || printf ','
      first=0
      printf '{"file":"%s","line":%s,"symbol":"%s","severity":"%s","hits":%s,"reason":"%s"}' \
        "$(json_escape "$f")" "${ln:-0}" "$(json_escape "$sym")" "$sev" "${n:-0}" "$(json_escape "$reason")"
    done <"$FINDINGS_FILE"
  fi
  printf '],"summary":{"blocker":%s,"warn":%s,"info":%s},"log":"%s"}\n' \
    "$N_BLOCKER" "$N_WARN" "$N_INFO" "$(json_escape "$OHOS_LOGFILE")"
}

#------------------------------------------------------------------------------
# 5. 主流程
#------------------------------------------------------------------------------
run_probe
[ "$DO_SCAN" = 1 ] && scan_files

if [ "$JSON" = 1 ]; then report_json; else report_text; fi

if [ "$PROBE_STATE" != "done" ] && [ "$FILES_WITH_CALLS" = 0 ]; then
  say_err "[warn] 探针未执行且无扫描命中，结论不确定（可用 --clang 指定目标平台编译器重跑）"
fi

if [ $((N_BLOCKER + N_WARN)) -gt 0 ]; then
  exit 10
fi
if [ "$DO_SCAN" = 0 ] && [ "$PROBE_STATE" = "done" ] && { [ "$HEADER_OK" = 0 ] || [ "$LINKINTL_OK" = 0 ]; }; then
  exit 10
fi
exit 0

