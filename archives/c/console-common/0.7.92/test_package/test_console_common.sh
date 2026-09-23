#!/bin/bash
# console-common 0.7.92 — OHOS 冒烟测试（自写，上游 0 测试用例）
#
# 断言依据（脚本全文核对）：
# - install-keymap 分支顺序（前 30 行）：--help（exit 0 + Usage）→ 无参
#   （exit 1 + Usage）→ NONE（exit 0）——均在任何外部命令/文件系统操作
#   之前触发；真实加载路径（fgconsole/loadkeys/tempfile）需 Linux VT，
#   非 root CI 不触达
# - dh_consoledata 为 dh_consoledata.in 的 @DHDIR@/@KMAPDIR@/@LCDDEP@
#   替换产物——断言无占位符残留 + perl -c 语法校验
#   （Debian::Debhelper::Dh_Lib 未提供 → 只 perl -c 不实际执行）
# - getkmapchoice.pl 为标记行后插入 common.pl 的产物——断言 common.pl 的
#   函数（declare_keymaps）已并入（Debconf::Client::ConfModule 未提供，
#   perl -c 不可用）
# - config.in / common.pl 落位（common.pl 纯 sub 定义无 use → perl -c 可用）
#
# 环境适配（实测）：非 root 判定用 HOME 存在性（toybox id -u 对大 uid 报
# bad uid）

set -uo pipefail

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }

is_root() { [ -z "${HOME:-}" ]; }

IKM="$(command -v install-keymap 2>/dev/null || true)"

echo "=== console-common 0.7.92 — OHOS 冒烟测试 ==="
echo

# T00 — 包已装入 env PATH（runenv bindirs）
if [ -z "$IKM" ]; then
    fail "install-keymap 不在 PATH（conan runenv 未注入）"
else
    pass "install-keymap 在 PATH: $IKM"
fi

PKG_ROOT=""
if [ -n "$IKM" ]; then
    PKG_ROOT="$(cd "$(dirname "$IKM")/.." && pwd)"
fi

# T01 — install-keymap --help：exit 0 + Usage（参数解析前分支，确定性行为）
if [ -n "$IKM" ]; then
    OUT="$(bash "$IKM" --help 2>&1)"; RC=$?
    if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q "Usage: install-keymap"; then
        pass "install-keymap --help exit 0 + Usage"
    else
        fail "--help 断言不符: RC=$RC OUT=$OUT"
    fi
else
    fail "install-keymap 缺失，跳过 --help"
fi

# T02 — install-keymap 无参：exit 1 + Usage
if [ -n "$IKM" ]; then
    OUT="$(bash "$IKM" 2>&1)"; RC=$?
    if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q "Usage: install-keymap"; then
        pass "install-keymap 无参 exit 1 + Usage"
    else
        fail "无参断言不符: RC=$RC OUT=$OUT"
    fi
else
    fail "install-keymap 缺失，跳过错参"
fi

# T03 — install-keymap NONE：exit 0（早退分支，先于 fgconsole/loadkeys/tempfile
#      ——不触达虚拟终端路径）
if [ -n "$IKM" ]; then
    OUT="$(bash "$IKM" NONE 2>&1)"; RC=$?
    if [ "$RC" -eq 0 ]; then
        pass "install-keymap NONE exit 0（早退分支，不触达 VT 路径）"
    else
        fail "NONE 断言不符: RC=$RC OUT=$OUT"
    fi
else
    fail "install-keymap 缺失，跳过 NONE"
fi

# T04 — kbd-config 在包内且可执行（#!/bin/sh 保留）
if [ -n "$PKG_ROOT" ] && [ -x "$PKG_ROOT/bin/kbd-config" ] && head -1 "$PKG_ROOT/bin/kbd-config" | grep -q '#!/bin/sh'; then
    pass "kbd-config 在包内且可执行（#!/bin/sh 保留）"
else
    fail "kbd-config 缺失/不可执行/shebang 不符"
fi

# T05 — dh_consoledata 占位符已全部替换（debhelper 客户端脚本，
#      Debian::Debhelper::Dh_Lib 未提供 → perl -c 不可用，断言止步于
#      落位/0755/占位符替换 + lcddep 版本串）
DH="$PKG_ROOT/bin/dh_consoledata"
if [ -n "$PKG_ROOT" ] && [ -x "$DH" ] && ! grep -qE '@(DHDIR|KMAPDIR|LCDDEP)@' "$DH" \
    && grep -q "console-common (>= 0.7.92)" "$DH" \
    && head -1 "$DH" | grep -q '#!/usr/bin/env perl -w'; then
    pass "dh_consoledata 占位符已替换（含 lcddep 版本串）+ env perl shebang"
else
    fail "dh_consoledata 缺失/占位符残留/shebang 未适配"
fi

# T06 — getkmapchoice.pl 标记行后已插入 common.pl（sub guess_arch 定义并入；
#      .in 本身只有 guess_arch 调用无定义 → 可作并入特征符号）
GK="$PKG_ROOT/share/console/getkmapchoice.pl"
if [ -n "$PKG_ROOT" ] && [ -x "$GK" ] \
    && awk '/#####COMMON#####/{f=1;next} f&&/^sub guess_arch/{print "YES";exit}' "$GK" | grep -q YES \
    && awk '/#####COMMON#####/{f=1;next} f&&/^\$::keymap_defs = \{/{print "YES";exit}' "$GK" | grep -q YES; then
    pass "getkmapchoice.pl 已并入 common.pl（sub guess_arch + \$::keymap_defs 存在）"
else
    fail "getkmapchoice.pl 缺失或 common.pl 未并入"
fi

# T07 — ps2-to-riscpc awk 脚本落位 + shebang 已适配
PS2="$PKG_ROOT/share/console/ps2-to-riscpc"
if [ -n "$PKG_ROOT" ] && [ -x "$PS2" ] && head -1 "$PS2" | grep -q '#!/usr/bin/env awk -f'; then
    pass "ps2-to-riscpc 落位且 shebang 为 #!/usr/bin/env awk -f"
else
    fail "ps2-to-riscpc 缺失/shebang 未适配"
fi

# T08 — common.pl 落位且独立 perl -c 可过（纯 sub 定义无 use 语句）
CP="$PKG_ROOT/share/debhelper/dh-consoledata/common.pl"
CI="$PKG_ROOT/share/debhelper/dh-consoledata/config.in"
if [ -n "$PKG_ROOT" ] && [ -f "$CP" ] && [ -x "$CI" ] \
    && perl -c "$CP" >/dev/null 2>&1 \
    && head -1 "$CI" | grep -q '#!/usr/bin/env perl -w'; then
    pass "common.pl perl -c syntax OK + config.in 落位（0755 + env perl shebang）"
else
    fail "common.pl/config.in 缺失或校验失败"
fi

echo
echo "=== 结果: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
