#!/bin/sh
# test_app.sh — ydpdict 1.0.5-1.1 平台级消费者验证（鸿蒙 PC / OHOS aarch64）
#
# 用法: sh test_app.sh <package_folder> <binary> <consumer_binary> [terminfo_dir]
#
# 覆盖三组独立断言:
#   OHOS-*  鸿蒙特有: 产物 ABI/装载契约（架构、静态 ncursesw、DT_NEEDED 无绝对路径）
#   TUI-*   消费者: 伪终端端到端跑通 ncurses 渲染与事件循环（pty_drive.py）
#   CONSUMER-* 消费者 C 程序（test_consumer.c 编译产物）的词典引擎 API 用例
#
# 说明：上游没有非交互 CLI 面（main() 解析参数后无条件 initscr()），故不做
# --version/--help 之类的 CLI 断言，程序的真实运行由 TUI-* 与 CONSUMER-* 覆盖。
# 退出码 = 失败断言数（0 = 全通过）。全程不写包目录，临时产物落在 $TMPDIR。
set -u

PKG=${1:?package folder}
BIN=${2:?ydpdict binary}
CONSUMER=${3:?consumer test binary}
TERMINFO_DIR=${4:-${TERMINFO:-}}

FAIL=0
N=0
# 临时产物一律落 $TMPDIR（R9），绝不写回配方树——conan 调 test_package 时 cwd
# 未必是构建目录，用相对路径曾把 _platform-check/ 写进 archives/ 并被提交（JC 拦截）。
WORK=""
for base in "${YDPDICT_TEST_WORK:-}" "${TMPDIR:-}" "$HOME/tmp" "$HOME"; do
    [ -n "$base" ] || continue
    mkdir -p "$base" 2>/dev/null || continue
    if mkdir -p "$base/ydpdict-test-$$" 2>/dev/null; then
        WORK="$base/ydpdict-test-$$"
        break
    fi
done
: "${WORK:=./_platform-check}"
rm -rf "$WORK"
mkdir -p "$WORK" 2>/dev/null || true
DUMP="$WORK/tui-screen.bin"
# 脚本自身目录（pty_drive.py 与脚本同处 test_package/）
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

pass() { N=$((N + 1)); echo "  [PASS] $1"; }
fail() { N=$((N + 1)); FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

# readelf 不一定在 PATH 中（OHOS 工具链布局），按候选顺序探测。
REF=""
for cand in "$(command -v readelf 2>/dev/null || true)" /data/service/hnp/bin/readelf \
            /usr/bin/readelf /bin/readelf; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then REF="$cand"; break; fi
done

echo "platform check: pkg=$PKG bin=$BIN"

# ---- OHOS-1: 产物存在且可执行 ----
if [ -x "$BIN" ]; then
    pass "OHOS-1 已安装的 bin/ydpdict 存在且可执行"
else
    fail "OHOS-1 已安装的 bin/ydpdict 缺失或不可执行 ($BIN)"
fi

# ---- OHOS-2: 设备 ABI（AArch64 ELF） ----
if [ -n "$REF" ]; then
    "$REF" -h "$BIN" > "$WORK/elf-header.txt" 2>&1
    if grep -q "AArch64" "$WORK/elf-header.txt"; then
        pass "OHOS-2 产物为 AArch64 ELF（与 OHOS 设备 ABI 一致）"
    else
        fail "OHOS-2 产物架构非 AArch64: $(grep Machine "$WORK/elf-header.txt" | head -n 1)"
    fi
else
    fail "OHOS-2 未找到 readelf，无法校验产物架构"
fi

# ---- OHOS-3: DT_NEEDED 不含 ncurses/panel/menu/tinfo 共享库（R4：OHOS 上共享
#      ncurses 会污染系统库；本配方静态链接 libncursesw.a） ----
if [ -n "$REF" ]; then
    "$REF" -d "$BIN" > "$WORK/elf-dynamic.txt" 2>&1
    if grep -E "NEEDED.*(libncurses|libpanel|libmenu|libtinfo|libform)" "$WORK/elf-dynamic.txt" > "$WORK/needed-curses.txt"; then
        fail "OHOS-3 DT_NEEDED 仍依赖共享 curses 库: $(cat "$WORK/needed-curses.txt")"
    else
        pass "OHOS-3 DT_NEEDED 无共享 curses 库（ncursesw 静态链接）"
    fi

    # ---- OHOS-4: DT_NEEDED 无构建机绝对路径条目（设备上不可解析） ----
    if grep -E "NEEDED.*\[?/.*\.so" "$WORK/elf-dynamic.txt" > "$WORK/needed-abs.txt"; then
        fail "OHOS-4 DT_NEEDED 含绝对路径条目: $(cat "$WORK/needed-abs.txt")"
    else
        pass "OHOS-4 DT_NEEDED 无绝对路径条目"
    fi
else
    fail "OHOS-3/4 未找到 readelf，无法校验动态依赖"
fi

# ---- 说明：本程序没有非交互 CLI 面，故不做 CLI 断言 ----
# 上游 main() 先 read_config(argc, argv)（只解析 TUI 配置项），随后无条件
# 调用 initscr()（src/ydpdict.c:797-799）——不存在 --version/-V/--help
# 之类会打印后退出的非交互分支，传这些参数同样进入全屏 TUI（实测：即使给
# --version，程序仍渲染词典加载界面并等待输入）。"程序真的能跑"由下面
# TUI-* 伪终端用例与 CONSUMER-C 消费者用例覆盖。

# ---- TUI-1/2: 伪终端端到端（无词典库、无用户配置的干净 HOME） ----
YDPDICT_TEST_TERMINFO="$TERMINFO_DIR" PYTHONIOENCODING=utf-8 \
    python3 pty_drive.py "$BIN" "$DUMP" 30 > "$WORK/tui-log.txt" 2>&1
TUI_RC=$?
if [ "$TUI_RC" -eq 0 ]; then
    pass "TUI-1 伪终端下 TUI 启动渲染并正常终止（退出键或 SIGTERM 兜底，rc=0）"
else
    fail "TUI-1 伪终端 TUI 运行失败 rc=$TUI_RC: $(head -n 3 "$WORK/tui-log.txt")"
fi
if [ -s "$DUMP" ] && grep -aqE "Unable to open dictionary|Please wait|ydpdict" "$DUMP"; then
    pass "TUI-2 首屏已渲染出 ydpdict 界面文案（ncursesw 终端层可用）"
else
    fail "TUI-2 首屏未渲染出 ydpdict 界面文案（dump $(wc -c < "$DUMP" 2>/dev/null || echo 0) 字节）"
fi

# ---- 消费者用例: 词典引擎 API（libydpdict 链接产物） ----
if "$CONSUMER" > "$WORK/consumer.txt" 2>&1; then
    pass "CONSUMER-C 消费者 C 程序全部断言通过（$(grep -o 'assertions=[0-9]*' "$WORK/consumer.txt" | tail -n 1)）"
else
    fail "CONSUMER-C 消费者 C 程序失败 rc=$?: $(grep -E 'FAIL' "$WORK/consumer.txt" | head -n 3)"
fi

echo "platform-check assertions=$N failures=$FAIL"
exit "$FAIL"
