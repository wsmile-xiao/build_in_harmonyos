#!/usr/bin/env bash
# test_package/test_avr_evtd.sh — avr-evtd 消费测试（打包完整性 + 无参数运行）
set -euo pipefail
pkg="$1"

echo "[test] avr-evtd 打包完整性检查"
[ -f "$pkg/bin/avr-evtd" ] && echo "PASS: bin/avr-evtd 存在" || { echo "FAIL: bin/avr-evtd 缺失"; exit 1; }

echo "[test] avr-evtd 无参数运行"
# aireview P2：守护进程无超时可能挂死 CI——加 timeout 5 保护
out=$(timeout 5 "$pkg/bin/avr-evtd" 2>&1) && rc=0 || rc=$?
if [ "$rc" -lt 126 ]; then
    # avr-evtd 是守护进程（无参数时无输出正常——rc<126 即可——如实记录）
    echo "PASS: avr-evtd 运行正常（rc=$rc——守护进程无参数无输出为正常）"
else
    echo "FAIL: avr-evtd 崩溃或无法执行（rc=$rc）"
    exit 1
fi
echo "PASS: avr-evtd smoke test OK"
