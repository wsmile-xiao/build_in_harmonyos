#! /bin/sh
# detect-case-insensitive-build.sh — 检测「大小写不敏感文件系统 + 仅大小写不同的构建规则」组合
#
# 用法: sh detect-case-insensitive-build.sh [源码目录] [日志文件]
# 退出码: 0 = 未见风险   1 = 命中风险   2 = 用法/目录错误
#
# 判定的两类风险:
#   A. 文件名冲突: 同一目录下存在仅大小写不同的文件名（构建中间产物与源文件最容易发生）
#   B. 规则冲突  : 构建规则中某条规则的「目标」与「前置」只差大小写（如 %.s86: %.S86）
#
# 输出同时写入 stdout 与日志文件（若给出）；脚本不吞输出、不使用管道 head，避免 SIGPIPE。

set -u

SRC=${1:-.}
LOG=${2:-}

say() {
  printf '%s\n' "$*"
  if [ -n "$LOG" ]; then printf '%s\n' "$*" >>"$LOG"; fi
  return 0
}

[ -d "$SRC" ] || { say "ERROR: 不是目录: $SRC"; exit 2; }

TMP="${TMPDIR:-/tmp}/casecheck.$$"
mkdir -p "$TMP" || { say "ERROR: 无法创建临时目录 $TMP"; exit 2; }
trap 'rm -rf "$TMP"' EXIT INT TERM

say "== detect-case-insensitive-build: $SRC"
say "   时间: $(date 2>/dev/null || echo unknown)   临时目录: $TMP"

# ---------------------------------------------------------------- 1. 文件系统探测
say ""
say "== 1) 文件系统大小写敏感性探测"
probe="$SRC/.caseprobe-$$-Aa"
FS=unknown
if : >"$probe" 2>/dev/null; then
  if [ -f "$SRC/.caseprobe-$$-aa" ]; then
    FS=insensitive
    say "   结果: 大小写【不敏感】（.caseprobe-$$-Aa 与 .caseprobe-$$-aa 是同一文件）"
  else
    FS=sensitive
    say "   结果: 大小写敏感（迁移到 HMDFS 等不敏感卷后本条风险才会复现）"
  fi
  rm -f "$probe" "$SRC/.caseprobe-$$-aa" 2>/dev/null
else
  say "   结果: 无法写入 $SRC（无法探测；请在可写目录重跑或改传可写源码副本）"
fi

# ---------------------------------------------------------------- 2. 文件名冲突
say ""
say "== 2) 目录内仅大小写不同的文件名（风险 A）"
find "$SRC" -maxdepth 3 -type f 2>/dev/null \
  | while IFS= read -r p; do printf '%s\n' "$(dirname "$p")/$(basename "$p")"; done \
  | tr 'A-Z' 'a-z' | sort | uniq -d >"$TMP/namecol"
if [ -s "$TMP/namecol" ]; then
  NAMECOL=1
  say "   命中（小写路径出现多次）："
  while IFS= read -r c; do say "     - $c"; done <"$TMP/namecol"
else
  NAMECOL=0
  say "   未发现仅大小写不同的文件名"
fi

# ---------------------------------------------------------------- 3. 规则冲突
say ""
say "== 3) 构建规则中目标/前置仅大小写不同（风险 B）"
find "$SRC" -maxdepth 4 -type f \
  \( -name 'Makefile' -o -name 'Makefile.*' -o -name '*.mk' -o -name '*.in' \
     -o -name 'CMakeLists.txt' -o -name '*.cmake' -o -name '*.pro' -o -name '*.meson' \) \
  2>/dev/null | sort >"$TMP/rules"
say "   扫描规则文件数: $(wc -l <"$TMP/rules" | tr -d ' ')"
: >"$TMP/rulehits"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  awk -v F="$f" '
    function low(s) { return tolower(s) }
    # 规则行: 目标 [: 前置...] 且非赋值/注释/条件行
    /^[^ \t#]/ && /:/ && !/[:]?=/ {
      line=$0
      sub(/[ \t]*#.*/, "", line)
      n=split(line, a, ":")
      if (n < 2) next
      t=a[1]
      gsub(/[ \t]/, "", t)
      if (t == "") next
      rest=a[2]
      m=split(rest, p, /[ \t]+/)
      for (i=1; i<=m; i++) {
        if (p[i] == "") continue
        if (p[i] != t && low(p[i]) == low(t)) {
          note = ""
          if (low(t) == "tags" || low(t) == "ctags" || low(t) == "tag" || low(t) == "id") {
            note = "   (automake 模板噪声，通常无害)"
          }
          printf "     - %s:%d  目标=[%s]  前置=[%s]%s\n", F, FNR, t, p[i], note
        }
      }
    }
  ' "$f" >>"$TMP/rulehits"
done <"$TMP/rules"
if [ -s "$TMP/rulehits" ]; then
  RULECOL=1
  say "   命中："
  cat "$TMP/rulehits" | while IFS= read -r l; do say "$l"; done
else
  RULECOL=0
  say "   未发现目标与前置仅大小写不同的规则"
fi

# ---------------------------------------------------------------- 4. 结论
say ""
say "== 4) 结论"
if [ "$RULECOL" = 1 ] && [ "$FS" = insensitive ]; then
  say "   【命中风险】不敏感文件系统 + 仅大小写不同的规则 ⇒ make 会把源文件当作「已存在的中间产物」，"
  say "     于是跳过该规则（下游工具读到未处理的输入）；若规则真的执行，输出又会原地替换源文件。"
  say "   处理策略见 strategy.md（S1 改中间后缀最小改动；S2 源外构建 + 显式别名规则；S3 env_unsupported 标记）。"
  exit 1
fi
if [ "$RULECOL" = 1 ]; then
  say "   【潜在风险】存在仅大小写不同的规则；当前文件系统大小写敏感，暂不失效，"
  say "   但迁移到 HMDFS/vfat 等不敏感卷即会复现（本类问题在鸿蒙 PC 上必现）。"
  exit 1
fi
if [ "$NAMECOL" = 1 ] && [ "$FS" = insensitive ]; then
  say "   【潜在风险】存在仅大小写不同的文件名（风险 A），不敏感卷上会互相覆盖。"
  exit 1
fi
say "   未发现该组合风险"
exit 0
