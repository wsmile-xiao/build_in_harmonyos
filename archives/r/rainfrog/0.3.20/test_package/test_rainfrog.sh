#!/bin/sh
# test_rainfrog.sh — 消费者侧真实执行 rainfrog 交付物（R34：真实执行 + 断言，非存在性）
# 用法: sh test_rainfrog.sh <pkg_dir>
set -u

PKG="${1:?usage: test_rainfrog.sh <pkg_dir>}"
BIN="$PKG/bin/rainfrog"
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { say "  [ok] $*"; }
bad()  { say "  [FAIL] $*"; FAIL=1; }

say "== rainfrog 交付物真实执行 =="
[ -x "$BIN" ] || { bad "binary not executable: $BIN"; exit 1; }

# ── ① --version 必须可用且报出 0.3.20 ───────────────────────────────
# 注：实测输出形如 `rainfrog 0.3.20-VERGEN_IDEMPOTENT_OUTPUT (2026-09-27)`
# —— 版本号后带 vergen 占位段（源码 tarball 无 git 仓库，vergen 取不到 git 描述）。
# 故只断言核心版本号 `0.3.20` 子串，不锚定整串。
if OUT=$("$BIN" --version 2>&1); then
  say "  --version → $(printf '%s' "$OUT" | head -1)"
  case "$OUT" in
    *0.3.20*) ok "--version 报出 0.3.20" ;;
    *)        bad "--version 未报出 0.3.20" ;;
  esac
else
  bad "--version 执行失败 rc=$?"
fi

# ── ② --help 必须可用且列出真实子命令 ──────────────────────────────
# 上游真实子命令只有 `edit` 与 `help`（TUI 为**无子命令时的默认行为**，
# 不存在 `query` 子命令——首版断言曾误写为 query，实测 rc=2）。
if OUT=$("$BIN" --help 2>&1); then
  say "  --help 首行: $(printf '%s' "$OUT" | head -1)"
  case "$OUT" in
    *edit*) ok "--help 列出 edit 子命令" ;;
    *)      bad "--help 未见 edit 子命令" ;;
  esac
else
  bad "--help 执行失败 rc=$?"
fi

# ── ③ 子命令 --help（证明 clap 命令树不止顶层）─────────────────────
if OUT=$("$BIN" edit --help 2>&1); then
  ok "edit --help 可用（首行: $(printf '%s' "$OUT" | head -1 | cut -c1-60)）"
else
  bad "edit --help 执行失败 rc=$?"
fi

# ── ④ 未知参数须以非零退出（错误路径不被吞掉）──────────────────────
if "$BIN" --definitely-not-a-flag >/dev/null 2>&1; then
  bad "未知参数竟以 0 退出"
else
  ok "未知参数以非零退出（错误路径正常）"
fi

say ""
if [ "$FAIL" -eq 0 ]; then
  say "OK: rainfrog 交付物 4 项断言全部通过"
  exit 0
else
  say "FAILED: rainfrog 交付物存在未通过断言"
  exit 1
fi
