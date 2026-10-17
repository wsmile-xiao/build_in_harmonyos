#! /bin/sh
# reproduce.sh — 复现并验证「大小写不敏感文件系统上 make 跳过中间产物规则」（样例库 mbr 1.2.2）
#
# 用法: sh reproduce.sh <源码目录> [工作目录] [日志目录]
#   <源码目录> : mbr 源码树（含 mbr.S86、Makefile.in、configure；应为未打补丁的原树）
#   [工作目录] : 默认 ${TMPDIR:-/tmp}/mbr-case-repro
#   [日志目录] : 默认 <工作目录>/logs
#
# 阶段 A: 未修复构建 → 期望 make 失败；make 认为中间产物 mbr.s86 已存在（实际是大小写不同的
#         源文件 mbr.S86），预处理配方 `%.s86: %.S86` 不执行，as86 直接汇编未预处理的源码，
#         报出 N 处 `unbound label`；源文件保持原样（未被改动）。
# 阶段 B: 应用策略 S1（中间后缀 .s86 -> .i86）→ 期望 make 通过、预处理步骤执行、0 处报错、
#         mbr.b = 512 字节、源文件保持原样。
#
# 退出码: 0 = 复现成功且策略验证通过   2 = 环境不满足（非大小写不敏感文件系统）
#         3 = 缺少构建工具             4 = 验证失败
# 依赖: as86（dev86）、xxd、patch、make、宿主 C 编译器
# 说明: 所有命令输出重定向到日志文件；脚本不使用 `| head` 之类会提前关闭管道的写法，规避 SIGPIPE。

set -u

SRC=${1:?用法: sh reproduce.sh <源码目录> [工作目录] [日志目录]}
WORK=${2:-${TMPDIR:-/tmp}/mbr-case-repro}
LOGD=${3:-$WORK/logs}
PATCH="$(dirname "$0")/../patches/0001-case-distinct-intermediate-suffix.patch"

note() { printf '%s\n' "$*"; }

count_lines() { # count_lines <pattern> <file>
  n=$(grep -c "$1" "$2" 2>/dev/null) || n=0
  [ -n "$n" ] || n=0
  printf '%s' "$n"
}

file_size() { wc -c <"$1" 2>/dev/null | tr -d ' ' ; }

same_file() { # same_file <a> <b> -> yes/no
  if cmp -s "$1" "$2" 2>/dev/null; then printf 'yes'; else printf 'no'; fi
}

# ------------------------------------------------------------------ 0. 环境检查
note "== mbr 大小写不敏感构建问题复现"
note "   源码目录: $SRC"
note "   工作目录: $WORK"
note "   日志目录: $LOGD"
note "   补丁    : $PATCH"

[ -d "$SRC" ] || { note "ERROR: 源码目录不存在: $SRC"; exit 4; }
[ -f "$PATCH" ] || { note "ERROR: 补丁不存在: $PATCH"; exit 4; }

missing=""
for t in as86 xxd patch make cmp; do
  command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
done
if [ -n "$missing" ]; then
  note "ERROR: 缺少构建工具:$missing"
  note "  as86/ld86 来自 dev86，xxd 来自 xxd 包，制品仓均有预编译包，可在构建期环境取用："
  note "    conan install --requires=dev86/0.16.21 --requires=xxd/9.1.0 \\"
  note "        -g VirtualBuildEnv -of build-tools"
  note "  或把它们的 bin 目录加入 PATH 后重跑本脚本。"
  exit 3
fi

mkdir -p "$WORK" "$LOGD" || { note "ERROR: 无法创建 $WORK / $LOGD"; exit 4; }

# 前置：必须位于大小写不敏感的文件系统，否则本问题不会复现
probe="$WORK/.caseprobe-$$-Aa"
if : >"$probe" 2>/dev/null; then
  if [ -f "$WORK/.caseprobe-$$-aa" ]; then
    note "   文件系统: 大小写【不敏感】（满足复现前提）"
  else
    note "ERROR: $WORK 位于大小写敏感的文件系统，本问题不会复现。"
    note "  请把工作目录指到 HMDFS 等大小写不敏感的卷上（例如鸿蒙 PC 的 /storage/hmdfs）。"
    rm -f "$probe"
    exit 2
  fi
  rm -f "$probe" "$WORK/.caseprobe-$$-aa" 2>/dev/null
fi

rm -rf "$WORK/phase-a" "$WORK/phase-b"

# ------------------------------------------------------------------ 1. 阶段 A：未修复
note ""
note "== 阶段 A：未修复构建（预期失败：中间产物规则被跳过）"
cp -R "$SRC" "$WORK/phase-a" || { note "ERROR: 复制源码树失败"; exit 4; }
cp "$WORK/phase-a/mbr.S86" "$LOGD/phase-a-mbr.S86.orig" 2>/dev/null || true

note "   A1 configure"
( cd "$WORK/phase-a" && ./configure ) >"$LOGD/phase-a-configure.log" 2>&1
note "      rc=$?  日志: $LOGD/phase-a-configure.log"

note "   A2 make -j1"
( cd "$WORK/phase-a" && make -j1 ) >"$LOGD/phase-a-make.log" 2>&1
rc_a=$?
note "      rc=$rc_a  日志: $LOGD/phase-a-make.log"

unbound_a=$(count_lines 'unbound label' "$LOGD/phase-a-make.log")
preproc_a=$(count_lines 'E -xc' "$LOGD/phase-a-make.log")   # 预处理配方是否执行
untouched_a=$(same_file "$WORK/phase-a/mbr.S86" "$LOGD/phase-a-mbr.S86.orig")
note "      as86 unbound label 条数   : $unbound_a"
note "      预处理步骤执行次数        : $preproc_a（未修复时应为 0：规则被跳过）"
note "      源文件 mbr.S86 是否保持原样: $untouched_a"

# ------------------------------------------------------------------ 2. 阶段 B：应用策略 S1
note ""
note "== 阶段 B：应用策略 S1（中间后缀 .s86 -> .i86）"
cp -R "$SRC" "$WORK/phase-b" || { note "ERROR: 复制源码树失败"; exit 4; }

: >"$LOGD/phase-b-patch.log"
if ( cd "$WORK/phase-b" && patch -p1 --dry-run ) <"$PATCH" >>"$LOGD/phase-b-patch.log" 2>&1; then
  ( cd "$WORK/phase-b" && patch -p1 ) <"$PATCH" >>"$LOGD/phase-b-patch.log" 2>&1
else
  note "ERROR: 补丁无法应用（源码树可能已打补丁），日志: $LOGD/phase-b-patch.log"
  exit 4
fi
note "      补丁已应用  日志: $LOGD/phase-b-patch.log"

note "   B1 configure"
( cd "$WORK/phase-b" && ./configure ) >"$LOGD/phase-b-configure.log" 2>&1
note "      rc=$?  日志: $LOGD/phase-b-configure.log"

note "   B2 make -j1"
( cd "$WORK/phase-b" && make -j1 ) >"$LOGD/phase-b-make.log" 2>&1
rc_b_make=$?
note "      rc=$rc_b_make  日志: $LOGD/phase-b-make.log"

unbound_b=$(count_lines 'unbound label' "$LOGD/phase-b-make.log")
preproc_b=$(count_lines 'E -xc' "$LOGD/phase-b-make.log")
untouched_b=$(same_file "$WORK/phase-b/mbr.S86" "$LOGD/phase-a-mbr.S86.orig")
if [ -f "$WORK/phase-b/mbr.b" ]; then
  size_b=$(file_size "$WORK/phase-b/mbr.b")
else
  size_b=missing
fi
note "      as86 unbound label 条数   : $unbound_b（应为 0）"
note "      预处理步骤执行次数        : $preproc_b（应 >= 1）"
note "      mbr.b 字节数              : $size_b（应为 512）"
note "      源文件 mbr.S86 是否保持原样: $untouched_b"

# ------------------------------------------------------------------ 3. 结论
note ""
note "== 结论"
ok=1
[ "$rc_a" -ne 0 ] 2>/dev/null || { note "   [FAIL] 阶段 A 未失败（make rc=$rc_a）：环境可能不满足复现前提"; ok=0; }
[ "$unbound_a" -ge 1 ] 2>/dev/null || { note "   [FAIL] 阶段 A 未出现 as86 unbound label（= $unbound_a）"; ok=0; }
[ "$preproc_a" -eq 0 ] 2>/dev/null || { note "   [FAIL] 阶段 A 预处理步骤竟然执行了（= $preproc_a），与预期机制不符"; ok=0; }
[ "$untouched_a" = "yes" ] || { note "   [FAIL] 阶段 A 源文件被改动（预期保持不变）"; ok=0; }
[ "$rc_b_make" -eq 0 ] || { note "   [FAIL] 阶段 B make rc=$rc_b_make"; ok=0; }
[ "$unbound_b" -eq 0 ] || { note "   [FAIL] 阶段 B 仍有 as86 报错（= $unbound_b）"; ok=0; }
[ "$preproc_b" -ge 1 ] 2>/dev/null || { note "   [FAIL] 阶段 B 预处理步骤未执行（= $preproc_b）"; ok=0; }
[ "$size_b" = "512" ] || { note "   [FAIL] 阶段 B mbr.b 字节数 = $size_b（期望 512）"; ok=0; }
[ "$untouched_b" = "yes" ] || { note "   [FAIL] 阶段 B 源文件被改动（预期保持不变）"; ok=0; }

if [ "$ok" = 1 ]; then
  note "   [PASS] 阶段 A 复现了「中间产物规则被跳过 → as86 汇编未预处理源码」，"
  note "          阶段 B 证明改中间后缀（.i86）可修复；两阶段的源文件都未被改动。"
  note "   全部日志: $LOGD"
  exit 0
fi
note "   详见日志: $LOGD"
exit 4
