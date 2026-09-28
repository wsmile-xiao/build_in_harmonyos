#!/bin/sh
# test_ballandpaddle.sh — ballandpaddle 0.8.1 消费者断言（真二进制实跑）
#
# 用法: sh test_ballandpaddle.sh <package_folder>
#
# 上游没有测试套件（Makefile.am 无 TESTS / check 目标），所以这里的断言全部打在
# **打包后的真实二进制**上，而不是编译一个 print-only 的 stub（R34）。
#
# 为什么这些断言是「鸿蒙特有」的：
#   src/main.cpp 的 main() 只做一件事 —— scm_boot_guile(argc, argv, inner_main, 0)。
#   --version / --help 的处理写在 inner_main() 里，而 inner_main 是 scm_boot_guile
#   的回调、在 Guile 初始化完成后才会被调用，且这两条路径在 initAudio() /
#   gameStateManager.init()（SDL 初始化）之前就 exit(0) —— 因此「能打印出版本串」
#   同时证明了：
#     1) 二进制在 OHOS 上可执行：动态加载器解析了 libguile-2.2.so 等全部 NEEDED；
#     2) 内嵌 Guile 2.2 解释器在 OHOS 上 boot 成功（含 ice-9 字节码加载路径）；
#     3) patches/0002 的 guile soname 探针修复生效（否则 configure 阶段就报
#        "can't find guile. This software REQUIRES guile."）。
#   未执行项：真正的游戏循环（SDL 显示 + 音频 + 从 BAP_DATADIR 读关卡/皮肤）
#   需要在有显示设备的目标机上运行，CI 沙箱无显示设备，故不在本脚本内执行。
set -e

PKG_ROOT="${1:?usage: test_ballandpaddle.sh <package_folder>}"
BIN="$PKG_ROOT/bin/ballandpaddle"

fail=0
count=0

ok()  { count=$((count + 1)); echo "ok   - $1"; }
bad() { count=$((count + 1)); fail=1; echo "FAIL - $1"; }

# check <描述> <输出文件> <grep 模式>
check() {
    if grep -q -e "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1"; fi
}

# run_ok <描述> <输出文件> <命令...>：命令须以 0 退出
run_ok() {
    desc="$1"; out="$2"; shift 2
    if "$@" > "$out" 2>&1; then ok "$desc"; else bad "$desc"; fi
}

WORK="${TMPDIR:-/tmp}/ballandpaddle-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# ── A. 产物存在且可执行 ──────────────────────────────────────────────────
if [ -x "$BIN" ]; then
    ok "bin/ballandpaddle 存在且可执行"
else
    bad "bin/ballandpaddle 不存在或不可执行"
fi

# ── B. 实跑 --version ────────────────────────────────────────────────────
run_ok "--version 以 0 退出" version.out "$BIN" --version
check "自报版本为 0.8.1（取自 AC_INIT）" version.out "ballandpaddle (GNU Ball and Paddle) 0\.8\.1"
check "版权行完整（version_ss 全串打印）" version.out "Copyright (C) 2007, 2008 Eric Hutchins"
check "许可证行" version.out "GNU General Public License"
check "免责声明行" version.out "There is NO WARRANTY"

# ── C. 实跑 --help ───────────────────────────────────────────────────────
run_ok "--help 以 0 退出" help.out "$BIN" --help
check "帮助含 Usage 段" help.out "Usage:"
check "帮助声明 --levelsetname" help.out "--levelsetname"
check "帮助声明 --levelsetfilename" help.out "--levelsetfilename"
check "帮助声明 --level 与 --version" help.out "--version"

# ── D. 实跑参数校验路径（均在 SDL/GUI 初始化之前返回） ───────────────────
run_ok "--level 缺值以 0 退出" level.out "$BIN" --level
check "缺值诊断文本" level.out "ballandpaddle: option requires argument -- level"
check "缺值时提示查看 --help" level.out "Try \`ballandpaddle --help' for more information."

run_ok "--level 1（三件套不全）以 0 退出" trio.out "$BIN" --level 1
check "三件套不全的诊断文本" trio.out "ballandpaddle: missing levelsetfilename"

# ── E. 安装布局：游戏运行必需的数据面（关卡/皮肤/字体）+ 桌面/手册/文档 ──
for f in \
    share/ballandpaddle/levelsets \
    share/ballandpaddle/FreeSans.ttf \
    share/ballandpaddle/kochi-gothic.ttf \
    share/ballandpaddle/images/menuback.png \
    share/ballandpaddle/images/splash.png \
    share/ballandpaddle/images/helpscreen.png \
    share/ballandpaddle/levels/utils.scm \
    share/ballandpaddle/levels/savannah/level1.scm \
    share/ballandpaddle/levels/tango/initialize.scm \
    share/ballandpaddle/levels/tango/skin.png \
    share/ballandpaddle/levels/tango/background.png \
    share/applications/ballandpaddle.desktop \
    share/man/man1/ballandpaddle.1 \
    share/doc/ballandpaddle/README ; do
    if [ -s "$PKG_ROOT/$f" ]; then
        ok "已安装 $f"
    else
        bad "缺失或无内容 $f"
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "ballandpaddle test_package: FAILED"
    exit 1
fi
echo "ballandpaddle test_package: all $count checks passed"
