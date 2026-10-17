#!/bin/sh
# test_package/test.sh — kfourinline 26.04.0 冒烟测试
# 用法: test.sh <kfourinline 二进制> <kfourinlineproc 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
set -eu

GUI="$1"
PROC="$2"

echo "[test] binaries: $GUI / $PROC"
test -x "$GUI"  || { echo "[test] ❌ kfourinline not executable"; exit 1; }
test -x "$PROC" || { echo "[test] ❌ kfourinlineproc not executable"; exit 1; }

# ---------- 断言 1: kfourinline --version ----------
echo "[test] $GUI --version"
OUT="$("$GUI" --version 2>&1)" || {
    echo "[test] ❌ --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *26.04.0*)
        echo "[test] ✅ --version reports 26.04.0"
        ;;
    *)
        echo "[test] ❌ unexpected version output"
        exit 1
        ;;
esac

# ---------- 断言 2: kfourinlineproc AI 进程启动握手 ----------
# kwin4proc 启动即向 stderr 打印 "AI process starts up"，然后进入
# stdin/stdout KGame IO 事件循环等待父进程（游戏主程序）的协议消息。
# 上游设计说明：该进程没有"stdin EOF 退出"路径——EOF 会让其 cookie
# 解析循环刷 "Cookie error" 日志且永不退出（协议上它只被父进程 spawn
# 并通过消息关闭）。因此测试采用「启动 → 捕获 banner → 1 秒后 TERM」
# 的握手验证：banner 出现即证明 ELF 加载、Qt 运行时初始化、KGame
# 进程对象构造全部成功。
echo "[test] $PROC startup banner (start, capture, TERM)"
set +e
"$PROC" > "$KFIPROC_OUT" 2>&1 &
PID=$!
# 轮询最多 5 秒等 banner 出现
i=0
FOUND=0
while [ $i -lt 25 ]; do
    if grep -q "AI process starts up" "$KFIPROC_OUT" 2>/dev/null; then
        FOUND=1
        break
    fi
    kill -0 $PID 2>/dev/null || break
    sleep 0.2
    i=$((i + 1))
done
if [ $FOUND -eq 1 ]; then
    echo "[test] ✅ kfourinlineproc startup banner observed"
    head -3 "$KFIPROC_OUT"
else
    echo "[test] ❌ kfourinlineproc did not print its startup banner"
    cat "$KFIPROC_OUT" 2>/dev/null
    kill -9 $PID 2>/dev/null
    exit 1
fi
kill -TERM $PID 2>/dev/null
wait $PID
RC=$?
set -e
# TERM 后退出码 143（128+15）或 0/1 均可接受（上游设计退出码为 1）
case "$RC" in
    0|1|143)
        echo "[test] ✅ kfourinlineproc terminated cleanly (rc=$RC)"
        ;;
    *)
        echo "[test] ❌ kfourinlineproc unexpected exit code $RC"
        exit 1
        ;;
esac

echo "[test] ALL SMOKE ASSERTIONS PASSED"
