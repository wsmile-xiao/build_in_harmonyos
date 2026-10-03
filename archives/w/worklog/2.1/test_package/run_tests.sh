#!/bin/sh
# =============================================================================
# worklog 2.1 — 真实功能测试（消费者视角）
#
# 全部用例都执行【被测包真实产出的 OHOS aarch64 可执行文件】并断言【真实产物】，
# 不使用 echo/print 空壳（R34 / CI L1d），且当 bin/ 被移走时必然失败
# （CI L1e 破坏性反向验证）。
#
# 用法: sh run_tests.sh <worklog-binary> <dir-with-example-config>
#
# 关键行为说明（由源码 + 实测确定）：
#   worklog 先读项目配置文件、为每个项目建立 <log>.<KEY> 账本，再 initscr()
#   进入全屏 TUI。没有 TTY 时 ncurses 在 initscr() 处报
#   "Error opening terminal" 并以 1 退出——但此前所有账本文件已落盘。
#   因此本套测试用「unset TERM + 有界 timeout」在 curses 初始化前后的边界上
#   做确定性断言：既验证了真实的配置解析/账本管理，又不会陷入 TUI 死循环。
# =============================================================================
# 关于 shell 选项的说明（有意偏离 code-style 的 `set -euo pipefail`）：
#   * 不用 `set -e`：本脚本的核心是**捕获**被测程序的非 0 退出码
#     （rc=1/rc=255 是被断言的预期值），`set -e` 会在断言前直接终止脚本。
#   * 不用 `set -o pipefail`：shebang 为 POSIX `sh`，dash 不支持该选项，
#     加上会直接报错退出。
#   * `set -u` 保留：所有变量在使用前均已赋值/带默认值。
set -u

BIN="${1:-}"
EXDIR="${2:-}"
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -n "$EXDIR" ] || EXDIR="$SELF_DIR"

PASS=0
FAIL=0
TIMEOUT_BIN=20

report() {
    # $1 = PASS|FAIL, $2 = 用例名, $3 = 细节
    if [ "$1" = "PASS" ]; then
        PASS=$((PASS + 1))
        printf '  [ok]   %-34s %s\n' "$2" "$3"
    else
        FAIL=$((FAIL + 1))
        printf '  [FAIL] %-34s %s\n' "$2" "$3"
    fi
}

# 在独立子 shell 中运行 worklog：清空 TERM 强制 ncurses 走确定性失败路径，
# 并用 timeout 兜底防止 TUI 死循环。stdout/stderr 合并落盘。
run_wl() {
    _out="$1"; shift
    ( unset TERM; exec timeout "$TIMEOUT_BIN" "$BIN" "$@" ) >"$_out" 2>&1
    echo $?
}

assert_rc_nonzero_nothang() {
    # 期望：非 0 退出（配置/终端错误），且不是 124（timeout 杀掉的挂起）
    _rc="$1"
    if [ "$_rc" = "124" ]; then
        return 1
    fi
    [ "$_rc" -ne 0 ] || return 1
    return 0
}

# "已推进到 curses 初始化"的判据。不同 ncurses 构建的报错文案不同：
#   * conan ncursesw（本仓依赖）： ncurses: cannot initialize terminal type ($TERM="unknown"); exiting
#   * 发行版 ncurses（本地对照）：   Error opening terminal: unknown.
# 两者都含 "terminal"，故以该子串做跨构建稳健判定：它出现即说明
# 配置解析与账本初始化都已走完，失败点只可能在终端初始化。
CURSES_MARKER="terminal"

# 等待文件在【另一个进程】的目录视图中可见。
#
# 为什么需要：OHOS CI worker 的临时目录在 HMDFS 上，存在目录项可见性滞后。
# worklog 的执行顺序是「先建 8 个 <log>.<KEY> 项目账本 → 再 fopen(log,"a")
# 建主账本 → 立刻 initscr() 退出」。主账本是【最后】创建的那个文件，
# 进程退出后紧接的 stat/find 未必已能看到它。本地 WSL(ext4) 无此现象。
wait_for_file() {
    _f="$1"
    _n=0
    while [ "$_n" -lt 10 ]; do
        [ -e "$_f" ] && return 0
        sleep 1
        _n=$((_n + 1))
    done
    return 1
}

# 统计目录下匹配指定前缀的文件数（仅用于报告，不作为断言依据，见下）。
#
# 为什么不用 `find ... | wc -l`：`wc -l` 数的是换行符个数，管道计数有歧义。
count_ledgers() {
    # 注意：模式必须【不加引号】才能触发 glob 展开（"$2" 加引号会禁用展开）
    ( set -- "$1"/$2
      # glob 未命中时 sh 保留字面量，此时 $1 不是真实路径
      if [ -e "$1" ]; then echo $#; else echo 0; fi )
}

# 为什么【不】把「账本文件总数」当作断言：
# 上游示例配置同时含 `R:Research` 与 `r:Reading NetNews` 两个仅大小写不同的键，
# worklog 以 `%s.%c` 拼账本名，得到 `wl.log.R` 与 `wl.log.r` 两个名字。
#   * 大小写敏感 FS（本地 ext4）→ 两个独立文件 → 共 9 个
#   * 大小写不敏感 FS（CI worker 的 /storage/.../tmp；实测 ls -a 只列出
#     wl.log.R，而 [ -f wl.log.r ] 为真）→ 两者合并 → 共 8 个
# 该数量由【文件系统大小写语义】决定，无法从配置推导，因此不能作为断言。
# 真正与平台无关的行为断言是下面两条，二者都保持严格：
#   1) 主账本存在
#   2) 配置里【每个】项目键的账本都可访问（[ -f <log>.<KEY> ] 全为真）
#      —— 在大小写不敏感 FS 上 wl.log.r 解析到 wl.log.R，该断言同样成立。

# 失败时把目录内容打出来，保证任何后续失败都能自解释（无需再猜）
dump_dir() {
    echo "      --- dir listing of $1 ---"
    ls -a "$1" 2>&1 | sed 's/^/      /'
}

# -----------------------------------------------------------------------------
echo "=== worklog 2.1 功能测试 ==="
echo "binary : $BIN"
if [ ! -x "$BIN" ]; then
    echo "FATAL: 被测可执行文件不存在或不可执行: $BIN" >&2
    exit 1
fi
BIN_SIZE=$(wc -c < "$BIN" | tr -d ' ')
echo "size   : ${BIN_SIZE} bytes"
echo

# --- T1 CLI 契约：-h 打印用法并以 0 退出 -------------------------------------
D=$(mktemp -d); RC=$(run_wl "$D/o" -h)
if [ "$RC" = "0" ] && grep -q "USAGE:" "$D/o"; then
    report PASS "T1_help_usage" "rc=0, 输出含 USAGE:"
else
    report FAIL "T1_help_usage" "rc=$RC, out=[$(head -c 80 "$D/o")]"
fi
rm -rf "$D"

# --- T2 上游自带示例配置：账本落盘（README 记载的官方验证流程）----------------
D=$(mktemp -d); RC=$(run_wl "$D/o" "$EXDIR/projects.example" "$D/wl.log")
wait_for_file "$D/wl.log"
N=$(count_ledgers "$D" 'wl.log*')
MISSING=""
for k in B L I R J P N r; do
    [ -f "$D/wl.log.$k" ] || MISSING="$MISSING $k"
done
if assert_rc_nonzero_nothang "$RC" && [ -f "$D/wl.log" ] \
   && [ -z "$MISSING" ] && grep -qi "$CURSES_MARKER" "$D/o"; then
    report PASS "T2_upstream_example_ledgers" "主账本 + 全部 8 个项目键账本均可访问 (实际文件数=${N}, 大小写不敏感 FS 上 R/r 会合并)"
else
    report FAIL "T2_upstream_example_ledgers" \
        "rc=$RC files=${N} main_log=$([ -f "$D/wl.log" ] && echo yes || echo no) missing=[${MISSING:-无}] reached_curses=$(grep -ci "$CURSES_MARKER" "$D/o")"
    dump_dir "$D"
fi
rm -rf "$D"

# --- T3 历史账本解析：预置合法条目后重跑，不应出现解析告警 ---------------------
# 注意：必须同时断言「程序真的跑到了 curses 初始化」——否则二进制装载失败
# （无输出）会被"没有告警"这个条件误判为通过。
D=$(mktemp -d)
printf '%s : %8.2f hours :  : [1.50 hours] : finished  Mon Jan  1 00:00:00 2026\n' \
    "BOWER consultation" > "$D/wl.log.B"
RC=$(run_wl "$D/o" "$EXDIR/projects.example" "$D/wl.log")
if assert_rc_nonzero_nothang "$RC" && grep -qi "$CURSES_MARKER" "$D/o" \
   && ! grep -q "Couldn't find" "$D/o"; then
    report PASS "T3_logfile_reparse" "已解析 [1.50 hours] 条目, 无 'Couldn't find' 告警"
else
    report FAIL "T3_logfile_reparse" \
        "rc=$RC reached_curses=$(grep -ci "$CURSES_MARKER" "$D/o") 告警=[$(grep -o "Couldn't find[^\"]*" "$D/o" | head -1)]"
fi
rm -rf "$D"

# --- T4 畸形配置：非冒号行必须被拒绝 ------------------------------------------
D=$(mktemp -d); printf 'X:ok\nBADLINE\n' > "$D/bad.projects"
RC=$(run_wl "$D/o" "$D/bad.projects" "$D/bad.log")
if [ "$RC" != "0" ] && [ "$RC" != "124" ] && grep -q "must be a colon" "$D/o"; then
    report PASS "T4_malformed_config" "rc=$RC, 正确报出冒号分隔符错误"
else
    report FAIL "T4_malformed_config" "rc=$RC out=[$(head -c 100 "$D/o")]"
fi
rm -rf "$D"

# --- T5 配置缺失：错误信息与退出码 -------------------------------------------
D=$(mktemp -d); RC=$(run_wl "$D/o" "$D/does-not-exist" "$D/x.log")
if [ "$RC" != "0" ] && [ "$RC" != "124" ] \
   && grep -q "cannot open project configuration file" "$D/o"; then
    report PASS "T5_missing_config" "rc=$RC, 正确报出配置缺失"
else
    report FAIL "T5_missing_config" "rc=$RC out=[$(head -c 100 "$D/o")]"
fi
rm -rf "$D"

# --- T6 【鸿蒙特有】DEFAULT_DIR_ENVVAR / HOME 默认工作目录 -------------------
# 源码 #ifdef DEFAULT_DIR_ENVVAR 分支：无参数启动时 chdir($HOME) 并采用
# 默认配置名 projects / 默认账本 worklog_time.log。这条路径依赖 POSIX
# getenv + chdir + 相对路径解析，在 OHOS 用户态沙箱下需要真机级验证。
D=$(mktemp -d); mkdir -p "$D/home"
cp "$EXDIR/projects.example" "$D/home/projects"
( unset TERM; HOME="$D/home"; cd "$D/home" && \
  exec timeout "$TIMEOUT_BIN" "$BIN" ) >"$D/o" 2>&1
RC=$?
wait_for_file "$D/home/worklog_time.log"
N=$(count_ledgers "$D/home" 'worklog_time.log*')
MISSING=""
for k in B L I R J P N r; do
    [ -f "$D/home/worklog_time.log.$k" ] || MISSING="$MISSING $k"
done
if assert_rc_nonzero_nothang "$RC" && grep -q "Using default directory" "$D/o" \
   && [ -f "$D/home/worklog_time.log" ] && [ -z "$MISSING" ]; then
    report PASS "T6_ohos_home_default_dir" "chdir(\$HOME) 生效, 默认账本 + 全部 8 个项目键账本均可访问 (实际文件数=${N})"
else
    report FAIL "T6_ohos_home_default_dir" \
        "rc=$RC files=${N} main_log=$([ -f "$D/home/worklog_time.log" ] && echo yes || echo no) missing=[${MISSING:-无}] out=[$(head -c 120 "$D/o")]"
    dump_dir "$D/home"
fi
rm -rf "$D"

# --- T7 【鸿蒙特有】产物为 AArch64 ELF（非宿主 x86_64）------------------------
# 纯 POSIX sh 读 ELF e_machine 字节（偏移 18，小端），0xB7 = EM_AARCH64。
# 不依赖 file/readelf 是否存在于 CI worker。
# 注：本用例断言的是「被测产物必须是 OHOS aarch64 构建」。若在 x86_64 Linux
# 上以 -pr os=Linux 自建本包（配方允许 Linux），此处会失败并给出明确提示——
# 这是期望行为：那种产物本就不是本用例要验证的 OHOS 交付物。
D=$(mktemp -d)
HEX=$(od -An -tx1 -j18 -N2 "$BIN" 2>/dev/null | tr -d ' \n')
case "$HEX" in
    b700|b7??) MACH="AArch64" ;;
    3e00)     MACH="x86-64" ;;
    2800)     MACH="ARM" ;;
    *)        MACH="unknown($HEX)" ;;
esac
if [ "$MACH" = "AArch64" ]; then
    report PASS "T7_ohos_aarch64_elf" "e_machine=0xB7 (EM_AARCH64), 非宿主架构"
else
    report FAIL "T7_ohos_aarch64_elf" "e_machine=$MACH, 期望 AArch64"
fi
rm -rf "$D"

# -----------------------------------------------------------------------------
echo
echo "=== 结果: ${PASS} passed, ${FAIL} failed ==="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
