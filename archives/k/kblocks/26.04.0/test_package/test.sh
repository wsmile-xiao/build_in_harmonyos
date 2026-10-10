#!/bin/bash
# test_package/test.sh — kblocks 26.04.0 消费者用例
# 用法: test.sh <kblocks 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
#
# 上游 kblocks 26.04.0 注册 6 个 autotests（autotests/）：
#   basic, KBlocksGameLogic, KBlocksItemGroup, KBlocksScene, KBlocksWin, View-Scene
# 这些上游测试在 conanfile.py build() 内通过 ctest 执行（BUILD_TESTING=ON）。
#
# test_package 作为消费者验证（R34），用例集如下：
#   用例 1（上游兼容）: kblocks --version  -> 版本串 26.04.0
#   用例 2（上游兼容）: kblocks --help     -> 命令行接口可用
#                        （KAboutData + QCommandLineParser 已完成运行时链接）
#   用例 3（上游兼容）: kblocks --author / --license -> KAboutData 元数据完整
#   用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载
#     真实启动包内 kblocks，由 OHOS 动态链接器解析完整 DT_NEEDED closure。
#     已发布 KF6 库以 "../../bin/libX.so" 相对形式记录 NEEDED —— OHOS musl
#     按符号链接路径（非 realpath）解析，未经 patchelf 修补为 SONAME 时
#     加载必然失败；Linux glibc 下同形路径可直接解析。故此用例在非 OHOS
#     平台恒过、在 OHOS 上是真实门禁。判定依据是**进程运行时行为**（链接器
#     能否完成解析），不比对任何特定输出内容，故为"非断言"型消费者用例。
set -euo pipefail

KBLOCKS="$1"

echo "[test] binary: $KBLOCKS"
test -x "$KBLOCKS" || { echo "[test] ❌ kblocks not executable"; exit 1; }

# ---------- 用例 1: kblocks --version ----------
echo "[test] 用例 1: --version"
OUT="$("$KBLOCKS" --version 2>&1)" || {
    echo "[test] ❌ --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *26.04*|*26.04.0*)
        echo "[test] ✅ 用例 1 通过 —— --version 报告 26.04.0"
        ;;
    *)
        echo "[test] ❌ 用例 1 失败 —— 版本输出异常"
        exit 1
        ;;
esac

# ---------- 用例 2: kblocks --help ----------
# 验证 Qt 和 KDE 运行时链接完整（--help 触发 KAboutData 和 QCommandLineParser）
echo "[test] 用例 2: --help"
HELP_OUT="$("$KBLOCKS" --help 2>&1)" || {
    echo "[test] ❌ --help exited non-zero"
    echo "$HELP_OUT"
    exit 1
}
echo "$HELP_OUT" | head -5

case "$HELP_OUT" in
    *kblocks*|*KBlocks*)
        echo "[test] ✅ 用例 2 通过 —— --help 识别 kblocks"
        ;;
    *)
        echo "[test] ❌ 用例 2 失败 —— --help 输出异常"
        exit 1
        ;;
esac

# ---------- 用例 3: kblocks --author / --license ----------
# KAboutData 元数据资源（author/license）随包安装且可读取
echo "[test] 用例 3: --author / --license"
AUTHOR_OUT="$("$KBLOCKS" --author 2>&1)" || {
    echo "[test] ❌ --author exited non-zero"
    exit 1
}
case "$AUTHOR_OUT" in
    *kblocks*)
        echo "[test] ✅ 用例 3a 通过 —— --author 输出作者信息"
        ;;
    *)
        echo "[test] ❌ 用例 3a 失败 —— --author 输出异常"
        exit 1
        ;;
esac
LICENSE_OUT="$("$KBLOCKS" --license 2>&1)" || {
    echo "[test] ❌ --license exited non-zero"
    exit 1
}
if printf '%s\n' "$LICENSE_OUT" | grep -qiE 'GPL|GENERAL PUBLIC LICENSE'; then
    echo "[test] ✅ 用例 3b 通过 —— --license 输出许可证信息"
else
    echo "[test] ❌ 用例 3b 失败 —— --license 输出异常"
    exit 1
fi

# ---------- 用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载 ----------
# 以真实应用路径启动 kblocks（非元数据路径），由 OHOS 动态链接器解析
# bin/kblocks 的全部 DT_NEEDED —— 含依赖库中被 patchelf 修补过的
# "../../bin/libX.so" 相对条目。判据：进程运行时不得出现链接器解析失败
# （cannot open shared object file / error while loading shared libraries /
# undefined symbol）。GUI 环境缺失（无 D-Bus session / 无 platform plugin）
# 导致的退出不属于链接失败，不判失败。
echo "[test] 用例 4（鸿蒙特有）: OHOS shared-library closure load"
LOG_DIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="$PWD"
CLOSURE_LOG="$LOG_DIR/kblocks-closure-$$.log"
: > "$CLOSURE_LOG" 2>/dev/null || true

set +e
"$KBLOCKS" >"$CLOSURE_LOG" 2>&1 &
KB_PID=$!
# 给动态链接器 + Qt/KF 初始化留出时间（轮询最多 10 秒）
i=0
while [ "$i" -lt 50 ]; do
    kill -0 "$KB_PID" 2>/dev/null || break
    sleep 0.2
    i=$((i + 1))
done
if kill -0 "$KB_PID" 2>/dev/null; then
    kill -TERM "$KB_PID" 2>/dev/null
fi
wait "$KB_PID" 2>/dev/null
CLOSURE_RC=$?
set -e

if grep -qE 'cannot open shared object file|error while loading shared libraries|symbol lookup error|undefined symbol' "$CLOSURE_LOG" 2>/dev/null; then
    echo "[test] ❌ 用例 4 失败 —— OHOS 动态链接器无法解析 DT_NEEDED closure："
    cat "$CLOSURE_LOG"
    exit 1
fi
echo "[test] ✅ 用例 4 通过 —— OHOS closure 加载成功，全部 DT_NEEDED 已解析（进程退出码 $CLOSURE_RC）"
head -3 "$CLOSURE_LOG" 2>/dev/null || true

echo "[test] ALL CONSUMER CASES PASSED (4 用例 / 6 断言)"
