#!/usr/bin/env bash
# demo.sh — OHOS NLS/gettext(libintl) 适配样例演示
#
# 阶段① 缺陷态：封装头缺 #include <libintl.h>
#        → 检测器 rc=10；conan create -o nls_mode=none 构建失败（dgettext 未声明）
# 阶段② 修复态：策略③ 兜底头（shim/include/libintl.h）
#        → 检测器 rc=0；conan create -o nls_mode=shim 构建成功（含 test_package）
# 阶段③（可选 --gettext）策略①：conan create -o nls_mode=gettext
#        → 需要环境提供真实 libintl.h + libintl，结果仅作信息展示（非阻断）
#
# 用法：bash demo.sh [--create] [--gettext]
# 环境：OHOS_PROFILE 覆盖 profile 路径；TMPDIR 覆盖工作/日志目录
# 说明：不使用 head 截断管道（避免 SIGPIPE 误判），过程输出重定向到 $WORK/demo.log
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
DETECT="$HERE/../detect-libintl-stub.sh"
REPO_ROOT="$(cd "$HERE/../../../.." && pwd)"
TMPBASE="${TMPDIR:-$HOME/tmp}"
WORK="$TMPBASE/ohos-libintl-demo"
LOG="$WORK/demo.log"
HEADER="$HERE/include/i18n-demo/i18n.h"
PROFILE="${OHOS_PROFILE:-$REPO_ROOT/ci/conan/profiles/ohos-aarch64}"

DO_CREATE=0
DO_GETTEXT=0
for a in "$@"; do
  case "$a" in
    --create)  DO_CREATE=1 ;;
    --gettext) DO_GETTEXT=1 ;;
    *) printf '未知参数: %s\n' "$a"; exit 2 ;;
  esac
done

mkdir -p "$WORK" || exit 2
: >"$LOG"
OVERALL=0
log()  { printf '%s\n' "$*" >>"$LOG"; }
say()  { printf '%s\n' "$*"; log "$*"; }
pass() { say "  ✓ $*"; }
fail() { say "  ✗ $*"; OVERALL=1; }

restore() { cp "$HERE/states/good/i18n.h.in" "$HEADER" 2>/dev/null || true; }
# conan create 会把 test_package 的构建目录落在源码树内，退出时清掉以保持可提交状态
cleanup() {
  restore
  rm -rf "$HERE/build" "$HERE/test_package/build" 2>/dev/null || true
}
trap cleanup EXIT

[ -f "$DETECT" ] || { printf '缺少检测脚本: %s\n' "$DETECT"; exit 2; }
[ -f "$HERE/states/bad/i18n.h.in" ] && [ -f "$HERE/states/good/i18n.h.in" ] || {
  printf '缺少状态模板目录 states/{bad,good}\n'; exit 2; }

say "== OHOS NLS/gettext(libintl) 样例演示 =="
say "sample : $HERE"
say "detect : $DETECT"
say "log    : $LOG"

# ---- 阶段① 缺陷态 -----------------------------------------------------------
say ""
say "[阶段①] 缺陷态：封装头缺 #include <libintl.h>"
cp "$HERE/states/bad/i18n.h.in" "$HEADER"
bash "$DETECT" --src "$HERE" --json >"$WORK/detect-bad.json" 2>>"$LOG"; RC_BAD=$?
SUM_BAD="$(grep -o '"summary":{[^}]*}' "$WORK/detect-bad.json" 2>/dev/null || true)"
log "phase1 detect rc=$RC_BAD $SUM_BAD"
if [ "$RC_BAD" = 10 ]; then
  pass "检测器按预期报出问题（rc=10）$SUM_BAD"
else
  fail "期望 rc=10，实际 rc=$RC_BAD $SUM_BAD"
fi

# ---- 阶段② 修复态 -----------------------------------------------------------
say ""
say "[阶段②] 修复态：策略③ 兜底头（shim/include/libintl.h）"
cp "$HERE/states/good/i18n.h.in" "$HEADER"
bash "$DETECT" --src "$HERE" --json >"$WORK/detect-good.json" 2>>"$LOG"; RC_GOOD=$?
SUM_GOOD="$(grep -o '"summary":{[^}]*}' "$WORK/detect-good.json" 2>/dev/null || true)"
log "phase2 detect rc=$RC_GOOD $SUM_GOOD"
if [ "$RC_GOOD" = 0 ]; then
  pass "检测器判为干净（rc=0）$SUM_GOOD"
else
  fail "期望 rc=0，实际 rc=$RC_GOOD $SUM_GOOD"
fi

# ---- 构建对比（--create）----------------------------------------------------
if [ "$DO_CREATE" = 1 ]; then
  say ""
  say "[构建对比] conan create --build=missing（CCACHE_DISABLE=1，避免缓存影响结论）"
  if [ ! -f "$PROFILE" ]; then
    say "  ! 未找到 profile: $PROFILE（可用 OHOS_PROFILE 指定）—— 跳过构建对比"
  else
    CRUN() { ( cd "$HERE" && CCACHE_DISABLE=1 conan create . -o "nls_mode=$1" -pr:a "$PROFILE" --build=missing ); }

    CRUN none >"$WORK/create-none.log" 2>&1; RC_NONE=$?
    log "create none rc=$RC_NONE"
    if [ "$RC_NONE" != 0 ] && grep -q 'dgettext' "$WORK/create-none.log"; then
      pass "缺陷态（nls_mode=none）按预期构建失败（rc=$RC_NONE，日志含 dgettext 报错）"
    else
      fail "缺陷态未见预期失败（rc=$RC_NONE），见 $WORK/create-none.log"
    fi

    CRUN shim >"$WORK/create-shim.log" 2>&1; RC_SHIM=$?
    log "create shim rc=$RC_SHIM"
    if [ "$RC_SHIM" = 0 ]; then
      pass "修复态（nls_mode=shim）conan create 成功（含 test_package 校验）"
    else
      fail "修复态（nls_mode=shim）conan create 失败（rc=$RC_SHIM），见 $WORK/create-shim.log"
    fi

    if [ "$DO_GETTEXT" = 1 ]; then
      CRUN gettext >"$WORK/create-gettext.log" 2>&1; RC_GT=$?
      log "create gettext rc=$RC_GT"
      say "  · 策略①（nls_mode=gettext）rc=$RC_GT（环境相关，仅信息展示，不参与判定）"
      say "    日志: $WORK/create-gettext.log"
    fi
  fi
else
  say ""
  say "[构建对比] 已跳过（加 --create 执行 conan create；--gettext 追加策略①对比）"
fi

say ""
if [ "$OVERALL" = 0 ]; then
  say "== 演示结果：PASS =="
  exit 0
fi
say "== 演示结果：FAIL =="
exit 1
