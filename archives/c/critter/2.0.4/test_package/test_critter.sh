#!/bin/sh
# test_package/test_critter.sh — critter 2.0.4 运行时冒烟测试（OHOS / aarch64）
#
# 由 test_package/conanfile.py 经 self.run(..., env="conanrun") 调用：
#   test_critter.sh <可写工作目录> <被测产物 stage 目录> <依赖 lib 目录(:分隔)>
#   其中 stage 目录需同时含 critter 与 resource.dat（两者必须同目录，
#   上游以 ./resource.dat 相对路径挂载资源包）
# 调用方把本脚本的 stdout 重定向到 <工作目录>/critter-run.log，因此末行的
# "RESULT: P passed, F failed" 就是 conanfile.py 解析的判据。
#
# 环境（conanrun 注入，本脚本不重复设置）：
#   LD_LIBRARY_PATH 各依赖包 lib/（gl4es 的 libGL.so.1、libpng16.so.16、libwebp* 等）
#   LIBGL_GLES / LIBGL_EGL
#                   critter 包 package_info().runenv_info 导出，
#                   gl4es 靠它们 dlopen /system/lib64/libGLESv3.so 与 libEGL.so
#
# 本脚本固定的无头相关变量：
#   SDL_VIDEODRIVER=invalid
#                   无显示环境下不让 SDL 落到任何可用驱动。用 dummy/offscreen 的
#                   风险是：在具备 EGL 的机器上可能建窗成功并进入游戏主循环，
#                   测试将挂死到超时；invalid 让 SDL_Init(VIDEO) 立刻失败，上游
#                   main() 随即走清理分支退出（实测 rc=0），而 gl4es 的 GL 栈、
#                   PhysFS 资源挂载、配置落盘在此之前都已完成，断言仍然有效。
#   SDL_AUDIODRIVER=dummy
#                   无音频设备；配合上游 -audio 0 关闭音频初始化
#   HOME=<工作目录>/home
#                   上游把可写数据（config.txt / leaderboard）写到 ~/.critter/，
#                   指向私有目录以免污染宿主 HOME 并便于断言落盘
#
# 退出码：全部断言通过为 0，否则为 1（RESULT 行同时给出计数）。
#
# 关于 shell 选项：只开 `set -u -o pipefail`、**刻意不开 `-e`**。本脚本按断言
# 逐项计数（ok()/bad() 累加），而 expect() 内部用 grep/比较判断期望，失配时返回
# 非 0 是"测试失败"这一正常路径而非脚本错误；开 `-e` 会在登记到 bad() 之前直接
# 中止，丢失逐项统计与末尾 RESULT 行（conanfile.py 正靠该行判定）。因此失败
# 由计数与退出码兜底，而不是靠 `-e`。
set -uo pipefail

WORK="${1:?usage: test_critter.sh <work dir> <staged pkg dir> <lib dirs>}"
PKGDIR="${2:?usage: test_critter.sh <work dir> <staged pkg dir> <lib dirs>}"
LIBDIRS="${3:-}"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "[assert] OK   : $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[assert] FAIL : $1"; }

RUN_DIR="$WORK/critter-run"
GAME_LOG="$WORK/critter-runtime.log"

# 依赖库目录由 conanfile.py 显式传入并在这里前置：外层包装 shell（OHOS /bin/sh=mksh）
# 可能重置 conanrun 注入的 LD_LIBRARY_PATH，前置后 libGL.so.1 / libc++_shared.so 等
# 一定能被加载器找到。
if [ -n "$LIBDIRS" ]; then
    LD_LIBRARY_PATH="$LIBDIRS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export LD_LIBRARY_PATH
fi
# gl4es 后端定位变量：正常情况下由被测包 package_info().runenv_info 经 conanrun 注入
# （其契约由 conanfile.py 的 runenv-contract 用例单独校验）；此处的兜底只为避免包装
# shell 丢环境导致假失败。
: "${LIBGL_GLES:=/system/lib64/libGLESv3.so}"
: "${LIBGL_EGL:=/system/lib64/libEGL.so}"
export LIBGL_GLES LIBGL_EGL

rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/home"
if ! cp "$PKGDIR/critter" "$RUN_DIR/critter"; then
    echo "[warn] 被测二进制复制失败（$PKGDIR/critter）——后续断言将以运行失败呈现"
fi
if ! cp "$PKGDIR/resource.dat" "$RUN_DIR/resource.dat"; then
    echo "[warn] 资源包复制失败（$PKGDIR/resource.dat）"
fi
chmod 755 "$RUN_DIR/critter" 2>/dev/null || true

echo "[case] run-smoke（无头启动 1 次，8 项断言）"
(
    cd "$RUN_DIR" || exit 1
    HOME="$RUN_DIR/home"; export HOME
    SDL_VIDEODRIVER=invalid; export SDL_VIDEODRIVER
    SDL_AUDIODRIVER=dummy; export SDL_AUDIODRIVER
    if command -v timeout >/dev/null 2>&1; then
        timeout 180 ./critter -fullscreen 0 -audio 0
    else
        ./critter -fullscreen 0 -audio 0
    fi
) > "$GAME_LOG" 2>&1
RC=$?

echo "----- critter 运行时输出（rc=$RC）开始 -----"
cat "$GAME_LOG" 2>/dev/null || echo "(无输出)"
echo "----- critter 运行时输出结束 -----"

if [ "$RC" -eq 0 ]; then
    ok "进程退出码 0（实际 $RC）"
else
    bad "进程退出码非 0（实际 $RC，124=超时）"
fi

expect() { # $1 断言描述  $2 日志正则
    if grep -qE "$2" "$GAME_LOG" 2>/dev/null; then
        ok "$1"
    else
        bad "$1（日志未匹配 /$2/）"
    fi
}

expect "gl4es 初始化" '^LIBGL: Initialising gl4es$'
expect "GLES 2.0 后端生效（/system/lib64/libGLESv3.so）" '^LIBGL: Using GLES 2\.0 backend$'
expect "gl4es 正常关闭" '^LIBGL: Shutting down$'
expect "引擎版本横幅 Critter 2.0.4" '^INFO: Critter 2\.0\.4'
expect "PhysFS 挂载资源包 ./resource.dat" '^INFO: \./resource\.dat$'
expect "可写数据目录已定位" '^INFO: Write Dir:'

if [ -f "$RUN_DIR/home/.critter/config.txt" ]; then
    ok "可写数据路径落盘（~/.critter/config.txt 已生成）"
else
    bad "可写数据路径未落盘（~/.critter/config.txt 缺失）"
fi

echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
    exit 0
fi
exit 1
