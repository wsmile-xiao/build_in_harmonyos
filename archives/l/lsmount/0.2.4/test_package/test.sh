#!/data/service/hnp/bin/bash
# test_package/test.sh — lsmount 0.2.4 消费者测试（R34 真断言：rc 判定 + 输出内容比对）
#
# 由 test_package/conanfile.py 的 test() 在 conanrun 环境下调用，被测对象是
# **已安装的 lsmount 二进制**（PATH 由 Conan 的 bindirs 注入），不是脚本自证。
#
# 断言分两类：
#   T1..T8  功能/回归断言 —— 用受控 fixture 输入驱动，逐条比对输出内容与退出码
#   T9      鸿蒙宿主真实数据断言 —— 直接解析本机 /proc/mounts 并与内核视图逐行对账
set -u

fail=0
pass() { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fail=1; }
chk()  { if [ "$2" = "0" ]; then pass "$1"; else bad "$1"; fi; }

if ! command -v lsmount >/dev/null 2>&1; then
    echo "FAIL: lsmount 不在 PATH（包未正确交付 bin/lsmount）"
    exit 1
fi

# ⚠ 临时件绝不落在测试目录里：Conan 直接把 test_package/ 当作 test 的 build folder
#   （实测 `Writing generators to .../archives/l/lsmount/0.2.4/test_package`），
#   在里面留 .live_pairs/.pairs.diff 这类隐藏文件会被 CI JC5「archives 未登记隐藏文件」拦。
#   OHOS 的 /tmp 只读 ⇒ 走 $TMPDIR，再退到 ~/tmp。
SCRATCH="${TMPDIR:-$HOME/tmp}/lsmount_tp.$$"
mkdir -p "$SCRATCH" || { echo "FAIL: 无法创建临时目录 $SCRATCH"; exit 1; }
trap 'rm -rf "$SCRATCH"' EXIT INT TERM

FIX="$SCRATCH/fixture_mounts.txt"
printf 'tmpfs /tmpx tmpfs rw,nosuid,relatime 0 0\n/dev/sda1 /mnt/one ext4 rw,relatime 0 0\n' > "$FIX" \
    || { echo "FAIL: 无法写 fixture"; exit 1; }

# ── T1: --help 退出码 + 帮助正文内容（含上游版本串与许可证） ──────────────
out=$(lsmount --help 2>&1); rc=$?
chk "T1a --help 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
echo "$out" | grep -qF "Usage: lsmount [options]"; chk "T1b 帮助含 Usage 行" "$?"
echo "$out" | grep -qF "Version: v0.2.4";          chk "T1c 帮助含 Version: v0.2.4" "$?"
echo "$out" | grep -qF "License: ISC";             chk "T1d 帮助含 License: ISC" "$?"
echo "$out" | grep -qF -- "-f, --use-file";         chk "T1e 帮助含 -f/--use-file 选项" "$?"

# ── T2: 核心功能 —— 把 mounts 表渲染成网格（默认隐藏未使用列） ────────────
out=$(lsmount -f "$FIX" 2>&1); rc=$?
lines=$(printf '%s\n' "$out" | grep -c .)
chk "T2a 渲染 fixture 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
chk "T2b 输出行数=2 (实际 $lines)" "$([ "$lines" = 2 ] && echo 0 || echo 1)"
printf '%s\n' "$out" | grep -qF "tmpfs /tmpx tmpfs rw,nosuid,relatime"
chk "T2c 含 tmpfs 行的四个字段" "$?"
printf '%s\n' "$out" | grep -qF "/dev/sda1 /mnt/one ext4 rw,relatime"
chk "T2d 含 /dev/sda1 行的四个字段" "$?"
printf '%s\n' "$out" | grep -q "0 0"; chk "T2e 默认隐藏未使用列(不应出现 '0 0')" "$([ "$?" = 1 ] && echo 0 || echo 1)"

# ── T3: --show-unused 让未使用列可见（与 T2e 互为反向断言） ───────────────
out=$(lsmount -u -f "$FIX" 2>&1); rc=$?
chk "T3a -u 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
printf '%s\n' "$out" | grep -qF "rw,nosuid,relatime 0 0"; chk "T3b -u 后出现未使用列 '0 0'" "$?"

# ── T4: --skip 过滤设备 ───────────────────────────────────────────────────
out=$(lsmount -s /dev/sda1 -f "$FIX" 2>&1); rc=$?
lines=$(printf '%s\n' "$out" | grep -c .)
chk "T4a -s 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
chk "T4b 被跳过的设备不出现" "$(printf '%s\n' "$out" | grep -qF '/mnt/one'; [ "$?" = 1 ] && echo 0 || echo 1)"
chk "T4c 仅剩 1 行 (实际 $lines)" "$([ "$lines" = 1 ] && echo 0 || echo 1)"

# ── T5: --print-vertical 每字段一行（2 行 × 4 列 = 8 行） ─────────────────
out=$(lsmount -v -f "$FIX" 2>&1); rc=$?
lines=$(printf '%s\n' "$out" | grep -c .)
chk "T5a -v 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
chk "T5b 纵向输出 8 行 (实际 $lines)" "$([ "$lines" = 8 ] && echo 0 || echo 1)"

# ── T6: --use-alignment 真实改变输出（列对齐产生填充） ────────────────────
a_bytes=$(lsmount -a -f "$FIX" 2>/dev/null | wc -c)
p_bytes=$(lsmount    -f "$FIX" 2>/dev/null | wc -c)
chk "T6a -a 对齐输出严格大于非对齐 ($a_bytes > $p_bytes)" "$([ "$a_bytes" -gt "$p_bytes" ] && echo 0 || echo 1)"

# ── T7: 颜色开关 —— -c 注入 ANSI 序列，-C（大写取反）不注入 ───────────────
ESC=$(printf '\033')
lsmount -c -f "$FIX" 2>/dev/null | grep -qF "${ESC}["; chk "T7b -c 输出含 ANSI 转义序列" "$?"
lsmount -C -f "$FIX" 2>/dev/null | grep -qF "${ESC}["; chk "T7c -C 输出不含 ANSI 转义序列" "$([ "$?" = 1 ] && echo 0 || echo 1)"

# ── T8: 错误路径 —— 输入文件不存在必须非零退出并给出原因 ─────────────────
err=$(lsmount -f ./no_such_file_for_lsmount 2>&1); rc=$?
chk "T8a 缺失输入文件退出码=1 (rc=$rc)" "$([ "$rc" = 1 ] && echo 0 || echo 1)"
printf '%s\n' "$err" | grep -qF "fopen"; chk "T8b 错误信息含 fopen 原因" "$?"

# ── T9: 鸿蒙宿主真实挂载表对账（消费者视角的鸿蒙特有断言） ────────────────
# 该断言只在真机上成立：/proc/mounts 内容是这台 HarmonyOS PC 的内核视图。
live=$(lsmount 2>&1); rc=$?
chk "T9a 默认(读 /proc/mounts) 退出码=0 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
n_out=$(printf '%s\n' "$live" | grep -c .)
n_ref=$(grep -c . /proc/mounts)
chk "T9b 渲染行数与 /proc/mounts 行数一致 (lsmount=$n_out proc=$n_ref)" \
    "$([ "$n_out" = "$n_ref" ] && echo 0 || echo 1)"
# 设备名+挂载点两列与内核逐行 1:1 对齐
printf '%s\n' "$live"  | awk '{print $1" "$2}' | sort > "$SCRATCH/live_pairs"
awk          '{print $1" "$2}' /proc/mounts | sort > "$SCRATCH/ref_pairs"
if diff "$SCRATCH/live_pairs" "$SCRATCH/ref_pairs" > "$SCRATCH/pairs.diff" 2>&1; then
    pass "T9c 设备+挂载点两列与 /proc/mounts 逐行完全一致（$n_ref 条）"
else
    bad  "T9c 设备+挂载点与 /proc/mounts 不一致"; head -4 "$SCRATCH/pairs.diff"
fi
# 鸿蒙专有文件系统类型必须被正确渲染（hmfs/erofs 只存在于 HarmonyOS）
printf '%s\n' "$live" | grep -qF "hmfs";   chk "T9d 渲染出鸿蒙 hmfs 文件系统" "$?"
printf '%s\n' "$live" | grep -qF "erofs";  chk "T9e 渲染出鸿蒙 erofs 文件系统" "$?"
printf '%s\n' "$live" | grep -q "hmmac=";  chk "T9f 保留鸿蒙 hmmac= 挂载选项原文" "$?"

echo "-----------------------------------------------------------"
if [ "$fail" = 0 ]; then
    echo "test lsmount 0.2.4: ALL PASS (9 组 / 28 条断言)"
else
    echo "test lsmount 0.2.4: FAILED"
fi
exit $fail
