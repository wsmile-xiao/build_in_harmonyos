#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — HarmonyOS 平台专项测试（R38 之外的平台语义验证）
#
# 上游 scripts/test.sh 只覆盖 CLI 行为，且其断言依赖 gcc/gcov；本脚本补充
# **鸿蒙特有**的验证维度（在 conanrun 环境执行，PATH 含包内 bin/）：
#   1. 二进制形态：ELF64/AArch64 + musl 解释器
#   2. 依赖面：DT_NEEDED 只有系统 libc.so（不携带构建机/conan 路径依赖）
#   3. 无 RPATH/RUNPATH（不得指向构建机 conan 缓存）
#   4. OHOS 标识与代码签名：.note.ohos.ident + .codesign 段存在（XPM 要求）
#   5. /proc 语义：zps 的扫描能枚举到本测试进程自身（OHOS procfs + musl
#      readdir 下 stat/cmdline 解析正确）
#   6. 内核线程过滤：列表不得出现 PPID=kthreadd(2) 的内核线程
#      （OHOS 内核线程命名与 Linux 不同，验证过滤口径）
#   7. 僵尸生命周期：制造 2 个真僵尸 → 检出 → 回收（-r -s CHLD，非破坏性）→ 消失
#   8. 信号名/信号号解析（-p -s <sig> 形式，对主机零副作用）
#   9. 非终端场景：stdout 不是 TTY 时颜色自动关闭（无 ANSI 转义序列）
#
# 僵尸工厂用 python3 fork()（父进程不 wait()，等价上游 example/zproc.c）；
# 环境无 python3 时仅第 7 项标记 SKIP。
#
# 刻意不启用 `set -e`：本脚本逐项判定并汇总（PASSED/DISCOVERED），
# 单条检查失败需继续执行后续检查、最后以 $fail 决定退出码。
set -uo pipefail

ZPS="$(command -v zps)" || { echo "FAIL: zps not on PATH"; exit 1; }
echo "[ohos-test] binary: $ZPS"

HAVE_PY=0
command -v python3 >/dev/null 2>&1 && HAVE_PY=1

work="$(mktemp -d)"
helper_pids=""
helper_flag=""
cleanup() {
    for p in $helper_pids; do kill "$p" 2>/dev/null; done
    rm -rf "$work"
}
trap cleanup EXIT
cd "$work"

# `|| true`：设备上可能既无 readelf 也无 llvm-readelf，此时留空并回退到二进制扫描
READELF="$(command -v readelf || command -v llvm-readelf || true)"
DISCOVERED=0
PASSED=0
SKIPPED=0
fail=0

ok()   { echo "OK:   $1"; PASSED=$((PASSED + 1)); }
bad()  { echo "FAIL: $1"; fail=1; }
skip() { echo "SKIP: $1"; SKIPPED=$((SKIPPED + 1)); }
case_() { DISCOVERED=$((DISCOVERED + 1)); }

list_zombies() { "$ZPS" -n 2>/dev/null | awk '$3 == "Z" { print $1, $2 }'; }

wait_zombie_count() {   # $1=ppid $2=want $3=timeout(s)
    local ppid="$1" want="$2" timeout="$3" i=0 n=0
    while [ "$i" -lt "$((timeout * 5))" ]; do
        n="$(list_zombies | awk -v p="$ppid" '$2 == p' | wc -l)"
        [ "$n" -ge "$want" ] && return 0
        i=$((i + 1)); sleep 0.2
    done
    echo "    (observed $n zombie(s) with ppid=$ppid after ${timeout}s)"
    return 1
}

wait_zombie_gone() {    # $1=ppid $2=timeout(s)
    local ppid="$1" timeout="$2" i=0 n=1
    while [ "$i" -lt "$((timeout * 5))" ]; do
        n="$(list_zombies | awk -v p="$ppid" '$2 == p' | wc -l)"
        [ "$n" -eq 0 ] && return 0
        i=$((i + 1)); sleep 0.2
    done
    echo "    ($n zombie(s) with ppid=$ppid still present after ${timeout}s)"
    return 1
}

# 制造 2 个真僵尸，父进程仅在收到**显式 SIGCHLD**、且测试落盘 flag 后才 wait()：
# 回收用 `zps -r -s CHLD` —— 与默认 `-r` 一样广播到**全系统**僵尸父进程，但 SIGCHLD
# 无害（默认处置不终止进程），默认 `-r` 的 SIGTERM 则会真正杀掉无关僵尸的父进程
# （实测发生过）。"非破坏性"来自信号选择，而非只发给自家 helper。
# 门控设计避免竞态：处理器先武装（晚到的显式 SIGCHLD 不会丢），
# 但子进程退出那一次 SIGCHLD 因 flag 不存在而不回收 → 僵尸得以保留供观察。
# 输出：$helper_pid（僵尸父进程 pid）、$helper_flag（允许回收的标记文件）
start_zombie_helper() {
    helper_flag="$work/reap-flag-$$-$RANDOM"
    python3 - "$helper_flag" <<'PYEOF' >/dev/null 2>&1 &
import os, signal, sys, time
flag = sys.argv[1]
def _reap(signum, frame):
    if not os.path.exists(flag):
        return
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
signal.signal(signal.SIGCHLD, _reap)
for _ in range(2):            # 两个立即退出的子进程 → 2 个 defunct
    if os.fork() == 0:
        os._exit(0)
time.sleep(300)
PYEOF
    helper_pid=$!
}

# 允许 helper 在下一次 SIGCHLD 时回收其僵尸（zps -r -s CHLD 会发出该信号）
arm_zombie_reap() {
    [ -n "$helper_flag" ] && : > "$helper_flag"
}

# "N/N"：signaled 与 defunct 自洽（发现的僵尸全部被成功发信号）
signaled_ratio_self_consistent() {
    awk '/Parent\(s\) signaled: [0-9]+\/[0-9]+/ {
             split($3, a, "/"); if (a[1] == a[2] && a[1] >= 1) { found = 1 }
         } END { exit !found }'
}

# ── 1. ELF64 + AArch64 + musl 解释器 ─────────────────────────
case_
elf_ok=0
musl_ok=0
if [ -n "$READELF" ]; then
    "$READELF" -h "$ZPS" 2>/dev/null | grep -qE "Class: +ELF64" \
        && "$READELF" -h "$ZPS" 2>/dev/null | grep -qE "Machine: +AArch64" && elf_ok=1
    "$READELF" -lW "$ZPS" 2>/dev/null | grep -q "ld-musl-aarch64.so.1" && musl_ok=1
else
    hdr="$(od -An -tx1 -N 20 "$ZPS" | tr -d ' \n')"
    case "$hdr" in 7f454c4602010100*) elf_ok=1 ;; esac
    [ "$(printf '%s' "$hdr" | cut -c37-40)" = "b700" ] || elf_ok=0
    grep -aq "ld-musl-aarch64.so.1" "$ZPS" && musl_ok=1
fi
if [ "$elf_ok" -eq 1 ] && [ "$musl_ok" -eq 1 ]; then
    ok "ELF64 AArch64 with musl interpreter (no readelf: $([ -z "$READELF" ] && echo yes || echo no))"
else
    bad "binary form unexpected (elf64/aarch64=$elf_ok musl=$musl_ok)"
fi

# ── 2. DT_NEEDED 只有系统 libc.so ────────────────────────────
case_
if [ -n "$READELF" ]; then
    needed="$("$READELF" -dW "$ZPS" 2>/dev/null | awk -F'[][]' '/NEEDED/ { print $2 }' | sort | tr '\n' ' ')"
    if [ "$needed" = "libc.so " ]; then
        ok "DT_NEEDED is exactly 'libc.so' (zero third-party runtime deps)"
    else
        bad "unexpected DT_NEEDED set: '$needed'"
    fi
else
    if grep -aq "libc\.so" "$ZPS"; then
        ok "no third-party runtime dependency strings in binary (fallback check)"
    else
        bad "libc.so not found in binary"
    fi
fi

# ── 3. 无 RPATH/RUNPATH（不得指向构建机/缓存） ───────────────
case_
rpath=0
if [ -n "$READELF" ]; then
    "$READELF" -dW "$ZPS" 2>/dev/null | grep -qiE "rpath|runpath" && rpath=1
else
    grep -aqE "/conan/|\.conan2/|/storage/Users/" "$ZPS" && rpath=1
fi
if [ "$rpath" -eq 0 ]; then
    ok "no RPATH/RUNPATH (self-contained single binary)"
else
    bad "RPATH/RUNPATH or build-host path present"
fi

# ── 4. OHOS 标识 + 代码签名段 ────────────────────────────────
case_
note_ok=0
sign_ok=0
if [ -n "$READELF" ]; then
    "$READELF" -SW "$ZPS" 2>/dev/null | grep -q "note.ohos.ident" && note_ok=1
    "$READELF" -SW "$ZPS" 2>/dev/null | grep -q "\.codesign" && sign_ok=1
else
    grep -aq "note.ohos.ident" "$ZPS" && note_ok=1
    grep -aq "\.codesign" "$ZPS" && sign_ok=1
fi
if [ "$note_ok" -eq 1 ] && [ "$sign_ok" -eq 1 ]; then
    ok "HarmonyOS ident note and .codesign section present"
else
    bad "OHOS ident/signature missing (ident=$note_ok codesign=$sign_ok)"
fi

# ── 5. /proc 语义：能枚举到本测试进程自身 ────────────────────
case_
self_pid=$$
out="$("$ZPS" -a -n 2>&1)"
if printf '%s' "$out" | awk -v p="$self_pid" '$1 == p { found = 1 } END { exit !found }'; then
    ok "-a enumerates this test process (pid=$self_pid) from OHOS /proc"
else
    bad "-a did not list this test process (pid=$self_pid)"
fi

# ── 6. 内核线程过滤（PPID=kthreadd=2 不得出现） ──────────────
case_
kthread_lines="$(printf '%s' "$out" | awk '$2 == 2')"
if [ -z "$kthread_lines" ]; then
    ok "kernel threads (ppid=2) are filtered out of the listing"
else
    bad "kernel threads leaked into listing: $(printf '%s' "$kthread_lines" | head -2)"
fi

# ── 7. 僵尸生命周期：检出 → 回收（SIGCHLD，非破坏性）→ 消失 ──
case_
if [ "$HAVE_PY" -eq 0 ]; then
    skip "zombie lifecycle (python3 unavailable on this host)"
else
    pre="$(list_zombies | wc -l)"
    # 注意：必须直接调用（不能用 $( ) 捕获），否则 helper_pid/helper_flag 的赋值
    # 只发生在子 shell 里，父 shell 拿不到 flag → 回收门控失效
    start_zombie_helper              # 该 helper 自带 2 个子进程 → 2 个僵尸
    h1="$helper_pid"
    helper_pids="$h1"
    if wait_zombie_count "$h1" 2 10; then
        # `-r -s CHLD`：只对本机全部僵尸父进程发 SIGCHLD（无害），由 helper 的
        # SIGCHLD 处理器完成真实回收。断言口径用「signaled/defunct 自洽」而非固定
        # 数值 —— 主机上可能同时存在无关僵尸（并发任务），固定 2/2 会误判。
        arm_zombie_reap
        out_r="$("$ZPS" -r -s CHLD 2>&1)"
        rc=$?
        if [ "$rc" -ne 0 ]; then
            bad "-r -s CHLD exited with $rc: $out_r"
        elif ! printf '%s' "$out_r" | signaled_ratio_self_consistent; then
            bad "-r -s CHLD did not report a self-consistent 'signaled: N/N': $out_r"
        elif wait_zombie_gone "$h1" 10; then
            ok "2 real zombies detected and reaped on OHOS via SIGCHLD (host had $pre zombie(s) before)"
        else
            bad "zombie(s) survived -r -s CHLD"
        fi
    else
        bad "could not create the 2 expected zombies"
    fi
fi

# ── 8. 信号名/信号号解析（全部非破坏性形式） ─────────────────
# 用 `-p -s <sig>` + 空 stdin：解析发生在连接信号之前，无僵尸时不会发信号、
# 有僵尸时也不会自动发信号（未选择编号），因此对主机上的其它进程零影响。
case_
sig_fail=""
for s in CHLD SIGTERM term 9 15; do
    printf '' | "$ZPS" -p -s "$s" >/dev/null 2>&1 || sig_fail="$sig_fail $s"
done
if [ -n "$sig_fail" ]; then
    bad "-p -s rejected valid signal forms:$sig_fail"
elif printf '' | "$ZPS" -p -s NOSUCHSIG >/dev/null 2>&1; then
    bad "-p -s NOSUCHSIG was accepted (invalid signal should be rejected)"
else
    ok "signal parsing: CHLD/SIGTERM/term/9/15 accepted, NOSUCHSIG rejected"
fi

# ── 9. 非终端场景颜色自动关闭（无 ANSI 转义） ────────────────
case_
# `|| true`：无 ANSI 转义时 grep -c 返回 1（匹配 0 行），计数 0 才是期望结果
out_plain="$("$ZPS" -n 2>/dev/null | od -c | grep -c '033' || true)"
# 同上：grep -c 无匹配返回 1，计数 0 为期望
out_col="$(  "$ZPS"   2>/dev/null | od -c | grep -c '033' || true)"
if [ "$out_plain" -eq 0 ] && [ "$out_col" -eq 0 ]; then
    ok "non-tty output has no ANSI escapes (colour auto-disabled)"
else
    bad "ANSI escapes emitted without a terminal (plain=$out_plain colour=$out_col)"
fi

echo "[ohos-test] checks: ${PASSED}/${DISCOVERED} passed, ${SKIPPED} skipped"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test_ohos.sh","discovered":%d,"passedCount":%d}\n' \
    "$([ "$fail" -eq 0 ] && echo true || echo false)" "$DISCOVERED" "$PASSED"

[ "$fail" -eq 0 ] || exit 1
echo "[ohos-test] all HarmonyOS-specific checks passed"
