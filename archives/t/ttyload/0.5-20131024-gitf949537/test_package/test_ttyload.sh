#!/bin/sh
# test_package/test_ttyload.sh — 真实执行 ttyload 的消费者测试。
#
# 口径说明（R34/R51）：ttyload 是 application 包，没有可链接的 API，所以"实质
# 依赖被测包"只能通过**执行它的二进制**来完成。上游自身也没有断言式测试
# （Makefile 里唯一的 test 目标是 './ttyload -i 1'，而 optstring 是
# "i:hvmr:c:"，没有任何"跑 N 帧后退出"的选项 —— 该命令按设计只能 Ctrl-C 结束），
# 所以这里做的是"有界执行 + 内容断言"：
#   T1 -v 版本横幅
#   T2 -h usage
#   T3 真跑一次绘图，断言标题行里出现的 1 分钟负载与内核 /proc/loadavg 一致
#      （这一条才是"arch 后端选对了"的实质证据）
#   T4 断言 ASCII 曲线确实被画出来（有 y 轴刻度 + 有数据点字符）
# 任何一条不成立都以非 0 退出，让 conan create 直接失败。

set -u

fails=0
fail() {
    printf 'FAIL: %s\n' "$1" >&2
    fails=$((fails + 1))
}
pass() { printf 'PASS: %s\n' "$1"; }

command -v ttyload >/dev/null 2>&1 || {
    printf 'FAIL: ttyload 不在 PATH 上（包未装出可执行文件？）\n' >&2
    exit 1
}
BIN=$(command -v ttyload)
printf '被测二进制: %s\n' "$BIN"
ls -l "$BIN"

# ---- T1: 版本横幅 ---------------------------------------------------------
# 上游 -v 的实现是"打印版本后继续掉进 usage 分支并 exit(1)"，这是上游设计，
# 所以这里只断言输出内容，不拿退出码当判据（退出码断言见 T3）。
OUT=$("$BIN" -v 2>&1 || true)
case "$OUT" in
    *"ttyload version 0.5.3"*) pass "T1 版本横幅 (0.5.3)" ;;
    *) fail "T1 版本横幅，实际输出: [$OUT]" ;;
esac

# ---- T2: usage ------------------------------------------------------------
OUT=$("$BIN" -h 2>&1 || true)
case "$OUT" in
    *"Usage: ttyload"*) pass "T2 usage 文本" ;;
    *) fail "T2 usage，实际输出: [$OUT]" ;;
esac

# ---- T3/T4: 有界真实渲染 --------------------------------------------------
WORKDIR=${TMPDIR:-$HOME/tmp}/ttyload-test.$$
mkdir -p "$WORKDIR" || { printf 'FAIL: 建不了临时目录 %s\n' "$WORKDIR" >&2; exit 1; }
# ttyload 不会自己退出；把 stdout 交给 head，读够 40 行后 head 关闭管道，
# ttyload 收到 SIGPIPE 自然终止 —— 有界、且不需要外部 timeout 命令。下面残留进程自检的
# 模式必须与实跑的命令行参数串一致（'-m -i 1'），早先写 '[t]tyload -i 1' 时永不匹配。
"$BIN" -m -i 1 </dev/null 2>"$WORKDIR/stderr.log" | head -n 40 >"$WORKDIR/plot.txt"
RES=$(ps -ef 2>/dev/null | grep '[t]tyload -m -i 1' | wc -l | tr -d ' ')
if [ "${RES:-0}" != "0" ]; then
    printf 'WARN: SIGPIPE 未按预期收尾，仍有 ttyload 残留进程\n' >&2
fi
PLOT_LINES=$(wc -l <"$WORKDIR/plot.txt" | tr -d ' ')

HDR=$(head -n 1 "$WORKDIR/plot.txt")
printf '首行: %s\n' "$HDR"
case "$HDR" in
    *"ttyload, v0.5.3"*) : ;;
    *) fail "T3 标题行缺少版本横幅: [$HDR]" ;;
esac

# 从标题行取 1 分钟负载（第一个形如 "21.25," 的字段）
REPORTED=$(printf '%s\n' "$HDR" | awk '{
    for (i = 1; i <= NF; i++) {
        f = $i
        sub(/,$/, "", f)
        if (f ~ /^[0-9]+\.[0-9]+$/) { print f; exit }
    }
}')
if [ -z "$REPORTED" ]; then
    fail "T3 标题行里取不到负载数字: [$HDR]"
else
    # 平台事实（B 机实测，见 notes.md「/proc 访问不对称」）：本机 SELinux 域内
    # 不是所有工具都能打开 /proc 下的文件 —— cat/head/sed/cut 与 shell 内建
    # read 可以，grep 与 awk 直接开文件会 Permission denied（stat 被拒）。
    # 所以这里取 /proc/loadavg 只用 sed + cut，不碰 grep/awk 的文件参数。
    KERNEL=$(sed -n '1p' /proc/loadavg 2>/dev/null | cut -f1 -d' ')
    if [ -z "$KERNEL" ]; then
        fail "T3 读不到 /proc/loadavg —— 被测包本身就依赖它，读不到就是平台适配问题，不能算通过"
    else
        printf 'ttyload 报出 1min load = %s，内核 /proc/loadavg = %s\n' "$REPORTED" "$KERNEL"
        # 两次读取之间负载会漂，3.0 的容差足够宽到不误杀，又足够紧到能证明
        # "它真的读了内核的负载数"而不是把 0 或随机值画出来。
        # awk 只在这里做算术（不打开任何文件），所以不受上面的限制。
        if awk -v a="$REPORTED" -v b="$KERNEL" 'BEGIN { d = a - b; if (d < 0) d = -d; exit (d <= 3.0 ? 0 : 1) }'; then
            pass "T3 负载数据与内核一致（arch/Linux getload 后端在 HarmonyOS 上取数正确）"
        else
            fail "T3 负载数据与内核不一致: ttyload=$REPORTED kernel=$KERNEL"
        fi
    fi
fi

# y 轴刻度 + 至少一个数据点字符（单色模式用 1..7 表示不同负载组合）
AXIS=$(grep -c '^[ ]*[0-9][0-9]*\.[0-9][0-9]*[ ]' "$WORKDIR/plot.txt" || true)
POINTS=$(tail -n +2 "$WORKDIR/plot.txt" | grep -c '[1-7]' || true)
printf 'y 轴刻度行数=%s  含数据点的行数=%s  总行数=%s\n' "$AXIS" "$POINTS" "$PLOT_LINES"
if [ "${AXIS:-0}" -ge 5 ] && [ "${POINTS:-0}" -ge 1 ] && [ "${PLOT_LINES:-0}" -ge 8 ]; then
    pass "T4 ASCII 曲线确实被画出"
else
    fail "T4 曲线未画出 (axis=$AXIS points=$POINTS lines=$PLOT_LINES)"
fi

rm -rf "$WORKDIR"

if [ "$fails" -ne 0 ]; then
    printf '\n%d 项失败\n' "$fails" >&2
    exit 1
fi
printf '\n全部 4 项通过\n'
