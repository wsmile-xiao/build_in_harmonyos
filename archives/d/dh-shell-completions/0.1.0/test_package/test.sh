#!/bin/bash
# dh-shell-completions 包产物内容断言测试
# 用法: test.sh <包内 bin 目录> <包根目录>
#
# 上游测试（tests/run.sh gen|composite|separate）已在配方 build() 内真实执行
# （见 conanfile.py 的 build()，需 perl + debhelper）。本脚本是消费者视角的
# 包产物断言：校验 Debian 安装布局被正确镜像 + 核心内容标记。
# 注意：测试必须读取包内产物（L1e——CI 破坏性测试会删除包 bin/ 后重跑本测试，
# 此时下列断言须失败）。

set -euo pipefail

BIN_DIR="${1:-}"
PKG_DIR="${2:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
  echo "FAIL: invalid bin dir '$BIN_DIR'" >&2
  exit 1
fi
if [ -z "$PKG_DIR" ] || [ ! -d "$PKG_DIR" ]; then
  echo "FAIL: invalid package dir '$PKG_DIR'" >&2
  exit 1
fi

fail=0

# [1] CLI 脚本存在（Debian 布局 /usr/bin → 包内 bin/）
if [ ! -f "$BIN_DIR/dh_shell_completions" ]; then
  echo "FAIL: missing $BIN_DIR/dh_shell_completions" >&2
  fail=1
fi

# [2] perl 序列 addon 模块存在（/usr/share/perl5 → 包内 share/perl5）
MOD="$PKG_DIR/share/perl5/Debian/Debhelper/Sequence/shell_completions.pm"
if [ ! -f "$MOD" ]; then
  echo "FAIL: missing $MOD" >&2
  fail=1
fi

# [3] dh_shell_completions 为 perl 脚本（shebang 经 patches/0001 适配为 env perl：
#     OHOS 无 /usr/bin/perl，perl 由 HNP 提供且位于 PATH）
if [ -f "$BIN_DIR/dh_shell_completions" ]; then
  if ! head -n 1 "$BIN_DIR/dh_shell_completions" | grep -q "^#!/usr/bin/env perl$"; then
    echo "FAIL: dh_shell_completions missing '/usr/bin/env perl' shebang" >&2
    fail=1
  fi

  # [4] 核心逻辑标记：依赖 debhelper Dh_Lib
  if ! grep -q "Debian::Debhelper::Dh_Lib" "$BIN_DIR/dh_shell_completions"; then
    echo "FAIL: dh_shell_completions lacks Dh_Lib dependency marker" >&2
    fail=1
  fi

  # [5][6][7] 三种 shell 的补全安装路径标记（bash / fish / zsh）
  if ! grep -q "bash-completion" "$BIN_DIR/dh_shell_completions"; then
    echo "FAIL: dh_shell_completions lacks bash completion path marker" >&2
    fail=1
  fi
  if ! grep -q "vendor_completions.d" "$BIN_DIR/dh_shell_completions"; then
    echo "FAIL: dh_shell_completions lacks fish completion path marker" >&2
    fail=1
  fi
  if ! grep -q "vendor-completions" "$BIN_DIR/dh_shell_completions"; then
    echo "FAIL: dh_shell_completions lacks zsh completion path marker" >&2
    fail=1
  fi

  # [8] 模式实现标记：generation 模式（mode=gen）在源码中存在
  if ! grep -q "process_gen" "$BIN_DIR/dh_shell_completions"; then
    echo "FAIL: dh_shell_completions lacks generation-mode marker" >&2
    fail=1
  fi
fi

# [9] perl 模块内容标记：以 insert_after 注册到 dh 序列
if [ -f "$MOD" ]; then
  if ! grep -q "insert_after" "$MOD"; then
    echo "FAIL: shell_completions.pm lacks insert_after sequence registration" >&2
    fail=1
  fi
  # [10] 模块依赖 debhelper Dh_Lib
  if ! grep -q "Debian::Debhelper::Dh_Lib" "$MOD"; then
    echo "FAIL: shell_completions.pm lacks Dh_Lib dependency marker" >&2
    fail=1
  fi
fi

if [ "$fail" -eq 1 ]; then
  echo "FAIL: dh-shell-completions package assertion failed" >&2
  exit 1
fi

echo "OK: dh-shell-completions package files present and content-consistent (10 assertions)"
