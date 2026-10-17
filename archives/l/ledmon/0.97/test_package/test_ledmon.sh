#!/bin/sh
# ledmon 0.97 消费者测试（N_consumer=5）：真实执行打包二进制并断言行为。
# ledmon/ledctl 是 root 守护进程 + SES 硬件数据面（本机无 enclosure、无 root），
# 可验证面 = ELF 可加载执行、静态依赖(libpci/libudev/sgutils2/librt)符号闭合、
# CLI 契约（--version/--help 退出码）、非 root 权限拒止路径。
#
# 有意不加 `set -e`：每条断言都要先拿到被测命令的非零退出码再判定，
# -e 会让 `out=$(cmd); rc=$?` 在断言之前就退出，反而丢掉真实错误。
set -u
set -o pipefail

if [ $# -lt 2 ]; then
    echo "FAIL: usage: $0 <ledctl> <ledmon>"
    exit 1
fi
LEDCTL="$1"
LEDMON="$2"
pass=0
fail=0
skip=0

ok()  { echo "PASS: $1"; pass=$((pass+1)); }
bad() { echo "FAIL: $1"; fail=$((fail+1)); }

# C1: ledctl --version 退出 0 且回显产品名（LED Control Application）与版本 0.97
out=$("$LEDCTL" --version 2>&1); rc=$?
case "$out" in *"LED Control Application"*0.97*) v=1;; *) v=0;; esac
if [ $rc -eq 0 ] && [ $v -eq 1 ]; then ok "C1 ledctl --version (rc=0, '$out')"; else bad "C1 ledctl --version rc=$rc out='$out'"; fi

# C2: ledctl --help 退出 0 且含 Usage 段
out=$("$LEDCTL" --help 2>&1); rc=$?
case "$out" in *USAGE*|*Usage*) v=1;; *) v=0;; esac
if [ $rc -eq 0 ] && [ $v -eq 1 ]; then ok "C2 ledctl --help"; else bad "C2 ledctl --help rc=$rc"; fi

# C3: ledmon --version 退出 0（daemon 的免特权分支）
out=$("$LEDMON" --version 2>&1); rc=$?
if [ $rc -eq 0 ]; then ok "C3 ledmon --version"; else bad "C3 ledmon --version rc=$rc out='$out'"; fi

# C4: ledmon --help 退出 0
out=$("$LEDMON" --help 2>&1); rc=$?
if [ $rc -eq 0 ]; then ok "C4 ledmon --help"; else bad "C4 ledmon --help rc=$rc"; fi

# C5: 非 root 执行特权命令 → 拒绝 'Only root can run this application.'
# 本机 id(1) 对虚拟化 uid 报 "id: bad uid <n>"（无 passwd 条目）并污染日志；
# 取不到数字一律按非 root 处理，正是本分支要测的场景。
uid=$(id -u 2>/dev/null || true)
if [ "$uid" != "0" ]; then
    out=$("$LEDCTL" set=normal /dev/nonexistent-sd 2>&1); rc=$?
    case "$out" in *"Only root"*) v=1;; *) v=0;; esac
    if [ $rc -ne 0 ] && [ $v -eq 1 ]; then ok "C5 non-root rejection (rc=$rc)"; else bad "C5 non-root rejection rc=$rc out='$out'"; fi
else
    # 以 root 运行时本条无从验证（真下发需要 SES/SGPIO 背板），计入 skip 而非静默丢弃，
    # 汇总行按 pass/fail/skip 三值输出，便于机器发现"少跑一条断言"。
    echo "SKIP: C5 (running as root, privileged-path rejection not verifiable)"; skip=$((skip+1))
fi

echo "CONSUMER-RESULT pass=$pass fail=$fail skip=$skip"
[ $fail -eq 0 ] || exit 1
exit 0
