#!/usr/bin/env bash
# test_package/test_canopenterm.sh — canopenterm 消费测试（打包完整性 + 可执行冒烟 + 上游单元测试套件）
set -euo pipefail
pkg="${1:?用法: 需传 pkg 路径 [可写工作目录]}"
workroot="${2:-${TMPDIR:-$HOME/tmp}}"
mkdir -p "$workroot"

echo "[test] canopenterm 打包完整性检查"
for f in bin/CANopenTerm bin/codb2json bin/run_unit_tests \
         lib/libCANvenient.so lib/libcjson.so lib/libSDL3.so \
         share/canopenterm/codb share/canopenterm/dbc share/canopenterm/eds; do
    [ -e "$pkg/$f" ] && echo "PASS: $f 存在" || { echo "FAIL: $f 缺失"; exit 1; }
done

echo "[test] 共享库 SONAME 检查（下游链接器寻址）"
for so in libCANvenient.so libcjson.so libSDL3.so; do
    soname=$(readelf -d "$pkg/lib/$so" 2>/dev/null | grep '(SONAME)' || true)
    [ -n "$soname" ] && echo "PASS: $so 有 SONAME" || { echo "FAIL: $so 缺少 SONAME"; exit 1; }
done

echo "[test] codb2json 可运行（无参 Usage 输出, rc=0）"
# -k 5: OHOS 程序捕获 SIGTERM，toybox timeout 先发 TERM 再补 KILL 确保可回收
out=$(timeout -k 5 10 "$pkg/bin/codb2json" </dev/null 2>&1) || rc=$?
rc=${rc:-0}
[ "$rc" -eq 0 ] || { echo "FAIL: codb2json rc=$rc"; echo "$out"; exit 1; }
echo "$out" | grep -q "Usage" || { echo "FAIL: codb2json 无 Usage 输出"; exit 1; }
echo "PASS: codb2json usage OK"

echo "[test] CANopenTerm -p 可启动（headless plain mode：进程存活=共享库全部加载成功）"
# CANopenTerm 安装信号处理器捕获 SIGTERM，timeout 无法终止它：
# 改为后台启动 + 存活判定（未崩溃=libSDL3/libCANvenient/libcjson 加载与链接 OK）+ kill -9
"$pkg/bin/CANopenTerm" -p </dev/null >/dev/null 2>&1 &
ct_pid=$!
sleep 5
# kill -0 无法区分「仍在运行」与「已退出但未被回收的僵尸」：僵尸进程 kill -0
# 恒返回成功，会把 5 秒内崩溃/缺库的进程误判为存活。改用 ps 状态判僵尸态（Z）：
# 仅当进程仍存活（state 非空且不含 Z）才判 PASS。
state=$(ps -o stat= -p "$ct_pid" 2>/dev/null || true)
state="${state//[[:space:]]/}"
if [ -n "$state" ] && [[ "$state" != *Z* ]]; then
    echo "PASS: CANopenTerm -p 启动后存活（依赖库加载成功，无崩溃）"
else
    # wait 在非零退出时返回非零，set -e 会直接中止脚本、丢掉 FAIL 判定与错误信息；
    # 用 rc=0 预置 + || rc=$? 兜底，确保崩溃/缺库场景仍能走到下面的 FAIL 分支。
    rc=0
    wait "$ct_pid" 2>/dev/null || rc=$?
    [ "$rc" -lt 126 ] || { echo "FAIL: CANopenTerm 崩溃或缺库 (rc=$rc)"; exit 1; }
    echo "PASS: CANopenTerm -p 快速正常退出 (rc=$rc)"
fi
kill -9 "$ct_pid" 2>/dev/null || true
wait "$ct_pid" 2>/dev/null || true

echo "[test] 上游单元测试套件 run_unit_tests（cmocka, cwd=包内 share/canopenterm 副本）"
# OHOS /tmp 只读：工作目录由 conanfile 传入（test build folder 可写）
workdir=$(mktemp -d "$workroot/ct_ut.XXXXXX") || { echo "FAIL: 无法创建可写工作目录 $workroot"; exit 1; }
trap 'rm -rf "$workdir"' EXIT
cp -r "$pkg/share/canopenterm/." "$workdir/"
out=$(cd "$workdir" && timeout -k 10 300 "$pkg/bin/run_unit_tests" 2>&1) || rc=$?
rc=${rc:-0}
[ "$rc" -eq 0 ] || { echo "FAIL: run_unit_tests rc=$rc"; echo "$out" | tail -20; exit 1; }
# cmocka 全通过时输出无 "FAILED" 行: grep 无匹配 rc=1，set -euo pipefail
# 下赋值管道非零会直接中止脚本，故解析一律 `|| true` 兜底
run_n=$(echo "$out" | grep -oE '[0-9]+ test\(s\) run' | grep -oE '^[0-9]+' | head -1 || true)
[ -n "$run_n" ] && [ "$run_n" -gt 0 ] || { echo "FAIL: 无法解析测试运行数"; echo "$out" | tail -20; exit 1; }
pass_n=$(echo "$out" | grep -oE 'PASSED[^0-9]*[0-9]+' | grep -oE '[0-9]+' | head -1 || true)
fail_n=$(echo "$out" | grep -oE 'FAILED[^0-9]*[0-9]+' | grep -oE '[0-9]+' | head -1 || true)
fail_n=${fail_n:-0}
pass_n=${pass_n:-0}
[ "$pass_n" = "$run_n" ] || { echo "FAIL: PASSED($pass_n) != run($run_n)"; echo "$out" | tail -20; exit 1; }
[ "$fail_n" -eq 0 ] || { echo "FAIL: $fail_n 个用例失败"; echo "$out" | tail -20; exit 1; }
echo "PASS: 上游单元测试 $pass_n/$run_n 通过"

echo "PASS: canopenterm test_package OK"
