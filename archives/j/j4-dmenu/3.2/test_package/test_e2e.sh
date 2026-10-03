#!/data/service/hnp/bin/bash
# test_package/test_e2e.sh — j4-dmenu 3.2 完整消费者用例（端到端）
#
# 由 test_package/conanfile.py 的 test() 在 `conan create` 的 test 阶段真实执行，
# $1 = 被测包最终安装的产物 <pkg>/bin/j4-dmenu-desktop（不是源码树中的中间产物）。
#
# 与 test.sh（冒烟：--version/--help）不同，本脚本是**真正跑通功能流程的消费者用例**：
# 构造一个隔离的 XDG 桌面环境 + 伪 dmenu（模拟真实 dmenu 的 stdin/stdout 协议），
# 驱动被测二进制走完整链路：扫描 .desktop → 解析 → 过滤 → 生成候选列表 →
# 呈现给 dmenu → 收回用户选择 → 组装命令行 → fork/execvp 启动目标程序，
# 并用"目标程序是否真的被启动、收到了什么参数"来验证结果（而非只看退出码）。
#
# 覆盖 7 个完整消费者用例（每个用例都是端到端，含真实进程启动）：
#   C1 基础全链路：候选列表内容正确 + 选中项被真实 execvp 启动 + 只启动选中项
#   C2 过滤语义：NoDisplay 项不进候选列表（端到端候选集断言）
#   C3 XDG DE 过滤：-x 依 XDG_CURRENT_DESKTOP 过滤 OnlyShowIn（kde 显示 / GNOME 隐藏）
#   C4 自定义输入直通：输入不在候选列表的任意命令 → 真实启动且参数原样传递
#   C5 非 ASCII（中文）条目：候选列表与真实启动双断言（鸿蒙中文环境常见）
#   C6 使用历史：--usage-log 首次记录 + 二次运行历史项排序优先（真实落盘/回读）
#   C7 wrapper 链路：--wrapper 包一层后仍能真实启动目标程序
#
# 另外含 C0 无头(no-DISPLAY)约束与 C8 --no-exec 干跑（不启动进程）作为边界用例。
#
# 所有断言 fail closed：任何非零退出 / 断言不成立都直接判失败，不做跳过。
set -euo pipefail

BIN="${1:-}"
[ -n "$BIN" ] || { echo "FAIL: usage: test_e2e.sh <pkg>/bin/j4-dmenu-desktop" >&2; exit 1; }
[ -x "$BIN" ] || { echo "FAIL: binary not executable: $BIN" >&2; exit 1; }
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"

# OHOS /system/bin/sh (mksh) 不能直接 exec ELF；一律用 bash 包裹执行（与 conanfile.py 一致）。
BASH_BIN="${CONFIG_SHELL:-}"
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
  BASH_BIN="$(command -v bash || true)"
fi
[ -n "$BASH_BIN" ] && [ -x "$BASH_BIN" ] \
  || { echo "FAIL: bash not found (CONFIG_SHELL/PATH) — required to execute ELF on OHOS" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ── 隔离的沙箱环境 ────────────────────────────────────────────────────────
# /tmp 在本机可能是只读 erofs，故优先用 TMPDIR，其次 <pkg>/..，最后 /tmp。
SANDBOX_BASE="${TMPDIR:-}"
if [ -z "$SANDBOX_BASE" ] || [ ! -w "$SANDBOX_BASE" ]; then
  SANDBOX_BASE="$(cd "$(dirname "$BIN")/.." && pwd)"
fi
W="$(mktemp -d "$SANDBOX_BASE/j4d-e2e-XXXXXX")" || fail "mktemp failed in $SANDBOX_BASE"
trap 'rc=$?; chmod -R u+rwX "$W" 2>/dev/null || true; rm -rf "$W" 2>/dev/null || true; exit $rc' EXIT

mkdir -p "$W/home/applications" "$W/empty"
CASES=0; PASSED=0
ok()   { PASSED=$((PASSED+1)); echo "  ✅ $*"; }
case_start() { CASES=$((CASES+1)); echo "[case C$1] $2"; }

# ── 伪 dmenu：复刻真实 dmenu 的 stdin/stdout 协议 ─────────────────────────
# 真实 dmenu 从 stdin 读候选列表并显示，把用户选中项写到 stdout。
# 本脚本用两个可注入变量模拟：J4D_CAPTURE=候选列表落盘位置，J4D_PICK=用户选择。
cat > "$W/fake-dmenu.sh" <<EOF
#!$BASH_BIN
# 读尽 stdin（= j4-dmenu 推来的候选列表）并落盘，然后输出"用户选择"。
while IFS= read -r line; do printf '%s\n' "\$line" >> "\${J4D_CAPTURE:?}"; done
printf '%s\n' "\${J4D_PICK:?}"
EOF
chmod +x "$W/fake-dmenu.sh"

# 目标程序：被选中后由 j4-dmenu execvp 真实启动，记录收到的参数（证明真跑通了）。
cat > "$W/target.sh" <<'EOF'
#!/data/service/hnp/bin/bash
{ printf 'argc=%s\n' "$#"; printf 'args=%s\n' "$*"; } > "$J4D_TARGET_OUT"
EOF
chmod +x "$W/target.sh"

# .desktop 条目：J4D E2E Marker（普通项）
cat > "$W/home/applications/j4d-e2e-marker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=J4D E2E Marker
Exec=$W/target.sh $W/ran-marker
Terminal=false
Categories=Utility;
EOF
# J4D E2E Hidden：NoDisplay=true，必须被过滤掉
cat > "$W/home/applications/j4d-e2e-hidden.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=J4D E2E Hidden
Exec=$W/target.sh $W/ran-hidden
NoDisplay=true
Terminal=false
EOF
# J4D E2E XdgDesk：OnlyShowIn=kde，只应出现在 KDE 会话
cat > "$W/home/applications/j4d-e2e-xdgdesk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=J4D E2E XdgDesk
Exec=$W/target.sh $W/ran-xdg
OnlyShowIn=kde;
Terminal=false
EOF
# 中文条目：验证非 ASCII 名称在鸿蒙中文环境下的完整链路
cat > "$W/home/applications/j4d-e2e-zh.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=J4D 中文 端到端测试
Exec=$W/target.sh $W/ran-zh
Terminal=false
EOF

# 基线环境：只暴露自建 XDG 目录，屏蔽宿主真实桌面项，保证断言确定。
export XDG_DATA_HOME="$W/home"
export XDG_DATA_DIRS="$W/empty"
export LC_MESSAGES=C
export J4D_CAPTURE="$W/capture.txt"
export J4D_TARGET_OUT="$W/target.out"
unset J4D_PICK

echo "[e2e] binary : $BIN"
echo "[e2e] sandbox: $W"
echo "[e2e] bash   : $BASH_BIN"

# 每次运行前清空可观测状态
reset_state() { rm -f "$W/capture.txt" "$W/target.out" "$W/ran-"* 2>/dev/null || true; }

# 以指定"用户选择"运行被测程序；返回其 stdout（不含 stderr）。
run_pick() { # $1=pick  $2..=额外参数
  local pick="$1"; shift
  rm -f "$W/capture.txt"
  J4D_PICK="$pick" "$BASH_BIN" -c "\"$BIN\" $*" 2>"$W/stderr.txt"
}

# ═══ C0 无头约束：鸿蒙 PC 无 DISPLAY，不得依赖 X；核心链路须能无 X 运行 ══════
case_start 0 "无头(headless)运行：不依赖 DISPLAY，--version/--help 正常"
if env -i PATH=/usr/bin:/bin LC_MESSAGES=C "$BASH_BIN" -c "unset DISPLAY; \"$BIN\" --version" > "$W/v.txt" 2>&1; then
  grep -q '3\.2' "$W/v.txt" || fail "C0: --version 未报告 3.2: $(cat "$W/v.txt")"
  ok "无 DISPLAY 时 --version 正常工作（输出 3.2）"
else
  fail "C0: 无 DISPLAY 时 --version 失败"
fi
if env -i PATH=/usr/bin:/bin LC_MESSAGES=C "$BASH_BIN" -c "unset DISPLAY; \"$BIN\" --help" >/dev/null 2>&1; then
  ok "无 DISPLAY 时 --help 退出码 0"
else
  fail "C0: 无 DISPLAY 时 --help 失败"
fi

# ═══ C1 基础全链路：候选列表 → 选择 → 真实 execvp 启动所选程序 ═══════════
case_start 1 "基础全链路：候选列表内容 + 选中项被真实启动 + 只启动选中项"
reset_state
run_pick "J4D E2E Marker" --dmenu="\"$W/fake-dmenu.sh\"" > "$W/c1.out" || fail "C1: 运行退出码非 0"
# 1a 候选列表：3 个可见项（Marker/XdgDesk/中文），NoDisplay 的 Hidden 不出现
[ -f "$W/capture.txt" ] || fail "C1: 未生成候选列表（dmenu 未收到数据）"
grep -qx 'J4D E2E Marker' "$W/capture.txt"   || fail "C1: 候选列表缺少 J4D E2E Marker"
grep -qx 'J4D E2E XdgDesk' "$W/capture.txt"  || fail "C1: 候选列表缺少 J4D E2E XdgDesk"
grep -qx 'J4D 中文 端到端测试' "$W/capture.txt" || fail "C1: 候选列表缺少中文条目"
[ "$(wc -l < "$W/capture.txt")" -eq 3 ] || fail "C1: 候选条数应为 3，实际 $(wc -l < "$W/capture.txt")"
ok "候选列表正确（3 项，含中文条目）"
# 1b 真实启动：目标程序被 execvp 执行并收到预期参数
# 注意 Exec=<程序> <参数>：首词是程序本身（argv[0]），故 target.sh 恰好收到 1 个参数。
[ -f "$W/target.out" ] || fail "C1: 选中项未被真正启动（无 target 输出）"
grep -qx 'argc=1' "$W/target.out" || fail "C1: 启动参数个数不符: $(cat "$W/target.out")"
grep -qx "args=$W/ran-marker" "$W/target.out" || fail "C1: 启动参数不符: $(cat "$W/target.out")"
ok "选中程序被真实 execvp 启动，Exec 参数原样传递"
# 1c 只启动选中项（未选中的项不得被执行）
[ ! -e "$W/ran-xdg" ] || fail "C1: 未选中的 XdgDesk 竟被启动"
[ ! -e "$W/ran-hidden" ] || fail "C1: NoDisplay 项竟被启动"
ok "仅启动选中项，未误启动其他条目"

# ═══ C2 NoDisplay 过滤语义（端到端候选集断言）═══════════════════════════
case_start 2 "NoDisplay=true 的条目不进候选列表"
reset_state
run_pick "J4D E2E Marker" --dmenu="\"$W/fake-dmenu.sh\"" >/dev/null || fail "C2: 运行失败"
if grep -q 'J4D E2E Hidden' "$W/capture.txt"; then
  fail "C2: NoDisplay 条目泄漏进候选列表"
fi
ok "NoDisplay 条目被正确过滤（候选列表无 J4D E2E Hidden）"

# ═══ C3 XDG DE 过滤：-x 依 XDG_CURRENT_DESKTOP 生效 ═════════════════════
case_start 3 "-x 按 XDG_CURRENT_DESKTOP 过滤 OnlyShowIn=kde 条目"
# OnlyShowIn 值按 XDG 规范大小写敏感，故用规范写法 "kde" 匹配。
reset_state
XDG_CURRENT_DESKTOP=kde J4D_PICK="J4D E2E Marker" "$BASH_BIN" -c "\"$BIN\" -x --dmenu=\"$W/fake-dmenu.sh\"" >/dev/null 2>&1 \
  || fail "C3: kde 会话下运行失败"
grep -qx 'J4D E2E XdgDesk' "$W/capture.txt" || fail "C3: kde 会话下 OnlyShowIn=kde 条目应出现"
ok "kde 会话：OnlyShowIn=kde 条目出现在候选列表"
reset_state
XDG_CURRENT_DESKTOP=GNOME J4D_PICK="J4D E2E Marker" "$BASH_BIN" -c "\"$BIN\" -x --dmenu=\"$W/fake-dmenu.sh\"" >/dev/null 2>&1 \
  || fail "C3: GNOME 会话下运行失败"
if grep -q 'J4D E2E XdgDesk' "$W/capture.txt"; then
  fail "C3: GNOME 会话下 OnlyShowIn=kde 条目不应出现"
fi
ok "GNOME 会话：OnlyShowIn=kde 条目被正确过滤"

# ═══ C4 自定义输入直通：不在候选列表的命令也能真实启动并透传参数 ══════════
case_start 4 "用户输入任意命令（不在候选列表）→ 真实启动且参数原样传递"
reset_state
cat > "$W/custom.sh" <<'EOF'
#!/data/service/hnp/bin/bash
printf 'custom=%s\n' "$*" > "$J4D_TARGET_OUT"
EOF
chmod +x "$W/custom.sh"
run_pick "$W/custom.sh hello world" --dmenu="\"$W/fake-dmenu.sh\"" >/dev/null || fail "C4: 运行失败"
[ -f "$W/target.out" ] || fail "C4: 自定义命令未被启动"
grep -qx 'custom=hello world' "$W/target.out" || fail "C4: 参数未原样传递: $(cat "$W/target.out")"
ok "自定义命令被真实启动，参数 hello world 原样到达目标程序"

# ═══ C5 非 ASCII（中文）条目完整链路 ════════════════════════════════════
case_start 5 "中文条目：候选列表与真实启动双断言"
reset_state
run_pick "J4D 中文 端到端测试" --dmenu="\"$W/fake-dmenu.sh\"" >/dev/null || fail "C5: 运行失败"
grep -qx 'J4D 中文 端到端测试' "$W/capture.txt" || fail "C5: 候选列表缺少中文条目"
[ -f "$W/target.out" ] || fail "C5: 中文条目选中后未被启动"
grep -qx "args=$W/ran-zh" "$W/target.out" || fail "C5: 中文条目启动参数不符: $(cat "$W/target.out")"
ok "中文条目端到端跑通（候选列表 UTF-8 保真 + 真实启动）"

# ═══ C6 使用历史：--usage-log 记录真实落盘，二次运行历史项排序优先 ════════
case_start 6 "--usage-log 首次记录 + 二次运行历史项排序优先"
reset_state
LOG="$W/usage.log"
rm -f "$LOG"
J4D_PICK="J4D 中文 端到端测试" "$BASH_BIN" -c "\"$BIN\" --usage-log=\"$LOG\" --dmenu=\"$W/fake-dmenu.sh\"" >/dev/null 2>&1 \
  || fail "C6: 首次运行失败"
[ -s "$LOG" ] || fail "C6: --usage-log 未生成/为空"
grep -q '端到端测试' "$LOG" || fail "C6: 使用历史未记录所选项: $(cat "$LOG")"
ok "使用历史真实落盘并记录所选项"
rm -f "$W/capture.txt"
J4D_PICK="J4D E2E Marker" "$BASH_BIN" -c "\"$BIN\" --usage-log=\"$LOG\" --dmenu=\"$W/fake-dmenu.sh\"" >/dev/null 2>&1 \
  || fail "C6: 二次运行失败"
FIRST="$(head -n1 "$W/capture.txt")"
[ "$FIRST" = "J4D 中文 端到端测试" ] || fail "C6: 历史项应排在候选首位，实际首位为 '$FIRST'"
ok "二次运行历史项排序优先（首位 = 上次所选项）"

# ═══ C7 wrapper 链路：--wrapper 包一层后仍能真实启动目标程序 ═════════════
case_start 7 "--wrapper：包装命令后仍能真实启动目标程序"
reset_state
cat > "$W/wrapper.sh" <<'EOF'
#!/data/service/hnp/bin/bash
printf 'wrapped=%s\n' "$*" > "$J4D_TARGET_OUT"
EOF
chmod +x "$W/wrapper.sh"
run_pick "J4D E2E Marker" --wrapper="\"$W/wrapper.sh\"" --dmenu="\"$W/fake-dmenu.sh\"" >/dev/null \
  || fail "C7: 运行失败"
[ -f "$W/target.out" ] || fail "C7: wrapper 未被调用"
grep -q 'wrapped=' "$W/target.out" || fail "C7: wrapper 输出不符: $(cat "$W/target.out")"
grep -q 'target.sh' "$W/target.out" || fail "C7: wrapper 未收到目标命令"
ok "wrapper 链路跑通（wrapper 收到完整目标命令行）"

# ═══ C8 --no-exec 干跑：组装命令行但不启动进程（边界用例）═══════════════
case_start 8 "--no-exec 仅输出组装后的命令，不启动任何进程"
reset_state
OUT="$(run_pick "J4D E2E Marker" --no-exec --dmenu="\"$W/fake-dmenu.sh\"")" || fail "C8: 运行失败"
printf '%s' "$OUT" | grep -q 'target.sh' || fail "C8: --no-exec 未输出组装后的命令: $OUT"
[ ! -e "$W/target.out" ] || fail "C8: --no-exec 竟启动了进程"
ok "--no-exec 输出组装命令且未启动进程"

# ═══ 汇总 ════════════════════════════════════════════════════════════════
echo "[e2e] 完整消费者用例：$CASES 个用例 / $PASSED 条断言全部通过"
echo "✅ test_package 端到端消费者测试 j4-dmenu/3.2 通过"
