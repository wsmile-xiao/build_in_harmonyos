#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 consumer test for the packaged `zps` CLI.
#
# zps 没有可链接的库接口，因此消费者测试驱动**打包后的二进制**完成
# 「真僵尸进程 → 检测 → 回收」闭环（zps 的唯一存在意义），并校验
# version/help/参数校验等 CLI 契约。
#
# 运行环境：test_package/conanfile.py 通过 `conanrun` 注入 PATH（含包内 bin/）。
# 僵尸进程工厂：python3 fork() 后父进程不 wait()（等价于上游 example/zproc.c），
# 若环境无 python3 则相关用例标记 SKIP（原因写入输出，不算失败）。
#
# 刻意不启用 `set -e`：本脚本是「跑完全部用例再统一判定」的聚合测试，
# 单条断言失败必须继续执行后续断言并汇总计数（最后以 $fail 决定退出码），
# 加 -e 会在首个失败处提前退出、丢掉其余用例的结果。
set -uo pipefail

ZPS="$(command -v zps)" || { echo "FAIL: zps not on PATH"; exit 1; }
echo "[test] zps on PATH: $ZPS"

HAVE_PY=0
command -v python3 >/dev/null 2>&1 && HAVE_PY=1

work="$(mktemp -d)"
helper_pid=""
helper_flag=""
cleanup() {
    [ -n "$helper_pid" ] && kill "$helper_pid" 2>/dev/null
    rm -rf "$work"
}
trap cleanup EXIT
cd "$work"

DISCOVERED=0
PASSED=0
SKIPPED=0
fail=0

ok()   { echo "OK:   $1"; PASSED=$((PASSED + 1)); }
bad()  { echo "FAIL: $1"; fail=1; }
skip() { echo "SKIP: $1"; SKIPPED=$((SKIPPED + 1)); }
case_() { DISCOVERED=$((DISCOVERED + 1)); }

# 列出当前系统中 state=Z 的进程，输出 "pid ppid" 两列（按 zps 的扫描顺序）
list_zombies() { "$ZPS" -n 2>/dev/null | awk '$3 == "Z" { print $1, $2 }'; }

# 等待「父进程为 $1 的僵尸进程」出现至少 $2 个，最多 $3 秒
wait_zombie_count() {
    local ppid="$1" want="$2" timeout="$3" i=0 n=0
    while [ "$i" -lt "$((timeout * 5))" ]; do
        n="$(list_zombies | awk -v p="$ppid" '$2 == p' | wc -l)"
        [ "$n" -ge "$want" ] && return 0
        i=$((i + 1))
        sleep 0.2
    done
    echo "    (observed $n zombie(s) with ppid=$ppid after ${timeout}s)"
    return 1
}

# 等待「父进程为 $1 的僵尸进程」全部消失，最多 $2 秒
wait_zombie_gone() {
    local ppid="$1" timeout="$2" i=0 n=1
    while [ "$i" -lt "$((timeout * 5))" ]; do
        n="$(list_zombies | awk -v p="$ppid" '$2 == p' | wc -l)"
        [ "$n" -eq 0 ] && return 0
        i=$((i + 1))
        sleep 0.2
    done
    echo "    ($n zombie(s) with ppid=$ppid still present after ${timeout}s)"
    return 1
}

# 制造一个真僵尸进程，并让父进程**只在收到显式 SIGCHLD 时才 wait()**。
# 回收用的是 `zps -r -s CHLD`：它与默认 `-r` 一样会把信号广播给**全系统**所有僵尸
# 进程的父进程，区别在于 SIGCHLD 是无害信号（默认处置下不终止任何进程），而默认
# `-r` 的 SIGTERM 会真正终止无关僵尸的父进程 —— 实测：一次运行中主机出现无关僵尸，
# 默认 -r 把它的父进程杀掉了。故"非破坏性"来自信号选择，而非只发给自家 helper。
#
# 门控设计（避免竞态）：SIGCHLD 处理器**先武装**、且只在测试落盘 flag 文件后
# 才真正 wait()。否则子进程退出时那一次 SIGCHLD 就会把僵尸立刻回收掉，
# 测试来不及观察到它；反过来若处理器晚于该信号才安装，显式 SIGCHLD 又会丢失。
# 输出：$helper_pid（僵尸父进程 pid）、$helper_flag（测试用于"允许回收"的标记文件）
start_zombie_helper() {
    helper_flag="$work/reap-flag-$$-$RANDOM"
    python3 - "$helper_flag" <<'PYEOF' >/dev/null 2>&1 &
import os, signal, sys, time
flag = sys.argv[1]
def _reap(signum, frame):
    if not os.path.exists(flag):   # 尚未允许回收 → 忽略（保留僵尸供测试观察）
        return
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
signal.signal(signal.SIGCHLD, _reap)   # 先武装，晚到的显式 SIGCHLD 不会丢
if os.fork() == 0:
    os._exit(0)                        # 子进程立即退出 → defunct(zombie)
time.sleep(300)
PYEOF
    helper_pid=$!
}

# 允许 helper 在下一次 SIGCHLD 时回收其僵尸（zps -r -s CHLD 会发出该信号）
arm_zombie_reap() {
    [ -n "$helper_flag" ] && : > "$helper_flag"
}

# "N/N"：zps 报告的 signaled/defunct 是否自洽（全部发现的僵尸都被成功发信号）
signaled_ratio_self_consistent() {
    awk '/Parent\(s\) signaled: [0-9]+\/[0-9]+/ {
             split($3, a, "/"); if (a[1] == a[2] && a[1] >= 1) { found = 1 }
         } END { exit !found }'
}

# ── 1. --version ─────────────────────────────────────────────
case_
out="$("$ZPS" -v 2>&1)"
if [ $? -eq 0 ] && printf '%s' "$out" | grep -q "zps v2.0.0"; then
    ok "-v prints the upstream version string (zps v2.0.0)"
else
    bad "-v output unexpected: $out"
fi

# ── 2. --help：8 个选项全部列出 ──────────────────────────────
case_
out="$("$ZPS" -h 2>&1)"
missing=""
for opt in -v -h -a -r -s -p -q -n; do
    printf '%s' "$out" | grep -q -- "$opt," || missing="$missing $opt"
done
if [ -z "$missing" ]; then
    ok "-h lists all 8 documented options"
else
    bad "-h misses options:$missing"
fi

# ── 3. 非 TTY 下列表输出：表头 + 退出码 0 ────────────────────
case_
out="$("$ZPS" -n 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | head -1 | grep -qE '^PID +PPID +STATE +NAME +COMMAND$'; then
    ok "no-tty listing prints the PID/PPID/STATE/NAME/COMMAND header (rc=0)"
else
    bad "listing header/rc unexpected (rc=$rc): $out"
fi

# ── 4. 真僵尸进程检测（zps 的核心功能） ──────────────────────
case_
if [ "$HAVE_PY" -eq 0 ]; then
    skip "zombie detection (python3 unavailable — no zombie factory on this host)"
else
    start_zombie_helper
    if wait_zombie_count "$helper_pid" 1 10; then
        ok "detects a real zombie (ppid=$helper_pid) via /proc"
    else
        bad "no zombie reported for ppid=$helper_pid"
    fi
fi

# ── 5. 真僵尸进程回收（-r -s CHLD：非破坏性，只回收自己的僵尸） ──
# 说明：默认 `-r`（SIGTERM）会向全系统所有僵尸父进程发信号，在共享主机上会误伤
# 无关进程；这里用 README 推荐的 SIGCHLD 组合，配合 helper 里按需 wait() 的
# SIGCHLD 处理器，既验证了真实回收，又不影响其它进程。
case_
if [ -z "$helper_pid" ]; then
    skip "zombie reaping (-r -s CHLD) (no zombie factory / no helper)"
else
    arm_zombie_reap
    out="$("$ZPS" -r -s CHLD 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        bad "-r -s CHLD exited with $rc: $out"
    elif ! printf '%s' "$out" | signaled_ratio_self_consistent; then
        bad "-r -s CHLD did not report a self-consistent 'signaled: N/N': $out"
    elif wait_zombie_gone "$helper_pid" 10; then
        ok "-r -s CHLD made the helper reap its zombie (SIGCHLD path, no side effects)"
    else
        bad "zombie survived -r -s CHLD for ppid=$helper_pid"
    fi
    kill "$helper_pid" 2>/dev/null
    helper_pid=""
fi

# ── 6. -p 提示模式在管道输入下可用（等价上游 printf '1' | zps -p） ──
# 同样用 -s CHLD 避免默认 SIGTERM 误伤（即便编号因并发僵尸错位，SIGCHLD 也无害）。
case_
if [ "$HAVE_PY" -eq 0 ]; then
    skip "-p with piped selection (python3 unavailable)"
else
    start_zombie_helper
    if ! wait_zombie_count "$helper_pid" 1 10; then
        bad "no zombie for -p case"
    else
        # zps -p 的编号即扫描顺序下标；按 list_zombies 的顺序取本僵尸的下标
        index="$(list_zombies | awk -v p="$helper_pid" '$2 == p { print NR; exit }')"
        arm_zombie_reap
        out="$(printf '%s' "$index" | "$ZPS" -p -s CHLD 2>&1)"
        rc=$?
        if [ "$rc" -eq 0 ] \
            && printf '%s' "$out" | grep -q "Enter process index(es) to proceed" \
            && printf '%s' "$out" | grep -q "PID (Z): " \
            && wait_zombie_gone "$helper_pid" 10; then
            ok "-p reads a piped index (index=$index) and reaps the selected zombie"
        else
            bad "-p piped selection failed (rc=$rc index=$index): $out"
        fi
    fi
    [ -n "$helper_pid" ] && kill "$helper_pid" 2>/dev/null
    helper_pid=""
fi

# ── 7. -s 必须与 -r/-p 同用（参数校验契约） ──────────────────
case_
out="$("$ZPS" -s 9 2>&1)"
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "The -s option has to be used with either -r or -p"; then
    ok "-s without -r/-p is rejected (rc=$rc)"
else
    bad "-s without -r/-p: rc=$rc out=$out"
fi

echo "[test] consumer checks: ${PASSED}/${DISCOVERED} passed, ${SKIPPED} skipped"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$([ "$fail" -eq 0 ] && echo true || echo false)" "$DISCOVERED" "$PASSED"

[ "$fail" -eq 0 ] || exit 1
echo "[test] all zps consumer checks passed"
