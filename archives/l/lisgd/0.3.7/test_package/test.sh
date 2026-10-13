#!/bin/sh
# lisgd 0.3.7 consumer smoke test: 真实执行被测包安装的 lisgd 二进制并断言行为。
# conanrun env 的 PATH 首位为包内 bin/，命令名解析到被测二进制（L1e 口径）。
# 用 set -eu 而非 set -euo pipefail：设备 toybox sh 无 pipefail，加了会直接报错退出。
set -eu

echo "--- lisgd 0.3.7 consumer verification ---"

# 0. 清空显示环境变量：lisgd 在 main() 里按 WAYLAND_DISPLAY/DISPLAY 与否分三条支路，
#    清空后分支确定 ⇒ 断言 4 的诊断串与退出码与运行机环境无关（否则 CI 有显示变量
#    时会走 wl_display_connect/XOpenDisplay 分支，断言变成环境相关的假红/假绿）。
unset DISPLAY 2>/dev/null || true
unset WAYLAND_DISPLAY 2>/dev/null || true
unset XDG_RUNTIME_DIR 2>/dev/null || true

# 1. 二进制已安装且 PATH 可解析
command -v lisgd >/dev/null 2>&1 || { echo "FAIL: lisgd not installed / not on PATH"; exit 1; }
b=$(command -v lisgd)
echo "PASS 1: lisgd installed -> $b"

# 2. 未知选项 ⇒ 上游 usage 分支并 exit(1)（lisgd.c:611-612），环境无关
set +e
out=$(lisgd --bogus 2>&1); rc=$?
set -e
echo "  raw: $out"
[ "$rc" -eq 1 ] || { echo "FAIL: unknown-option rc=$rc (expect 1)"; exit 1; }
echo "$out" | grep -q "lisgd \[-v\] \[-d /dev/input/0\]" || {
    echo "FAIL: usage line not printed"; exit 1; }
echo "PASS 2: unknown option -> usage + exit 1"

# 3. -h 缺值 ⇒ 上游 die("option -h expects a value")（lisgd.c:542）并 exit(1)
set +e
out=$(lisgd -h 2>&1); rc=$?
set -e
echo "  raw: $out"
[ "$rc" -eq 1 ] || { echo "FAIL: -h-no-value rc=$rc (expect 1)"; exit 1; }
echo "$out" | grep -q "option -h expects a value" || {
    echo "FAIL: missing-value diagnostic not printed"; exit 1; }
echo "PASS 3: -h without value -> die() + exit 1"

# 4. 无参数 + 无显示环境 ⇒ 确定诊断 + exit(1)，且**全程无动态加载错误**
#    （这一条是 test_package 的核心价值：证明 conan 依赖注入后
#      libinput/libwayland-client/libX11 及其传递依赖在运行期全部解析成功）
set +e
out=$(lisgd 2>&1); rc=$?
set -e
echo "  raw: $out"
case "$out" in
    *"Error loading shared library"*|*"Error relocating"*|*"symbol not found"*)
        echo "FAIL: runtime dynamic loader error (dependency injection broken)"
        exit 1 ;;
esac
[ "$rc" -eq 1 ] || { echo "FAIL: no-arg rc=$rc (expect 1)"; exit 1; }
echo "$out" | grep -q "Cannot detect display environment" || {
    echo "FAIL: display diagnostic not printed"; exit 1; }
echo "PASS 4: no-arg -> display diagnostic + exit 1 + zero loader errors"

echo "test lisgd 0.3.7: 4/4 checks PASS"
