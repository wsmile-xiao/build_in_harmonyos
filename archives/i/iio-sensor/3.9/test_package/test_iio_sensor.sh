#!/bin/bash
# test_iio_sensor.sh — verify packaged iio-sensor binaries, FAIL-CLOSED (R03)
# Called by test_package/conanfile.py test() method.
#
# R03 Review 修复（PR #11806 High Priority）：
# - 契约链两侧固定传递两个包内绝对路径：<pkg>/libexec/iio-sensor-proxy 与
#   <pkg>/bin/monitor-sensor（见 test_package/conanfile.py 与配方 package_info
#   bindirs=["bin","libexec"]）。任一缺失都代表打包不完整，**必须 FAIL exit 1**，
#   不得再以「WARN skip + 另一二进制置 1」的方式静默通过（缺失即失败）。
# - 期望数量 = 传入参数个数：两个期望产物**全部**真实存在才算通过；
#   缺任何一个 → 输出 FAIL 并以非零退出码结束（失败可观测）。
# - 可执行项（monitor-sensor）在可执行主机上实际运行 --help：断言退出码 0 且
#   输出含 Usage；x86 跨编译 worker 的 Exec format error（126/127）回退 ELF 校验
#   并如实标注，不作为通过依据。
# - iio-sensor-proxy（daemon）必须真实存在（libexec 或由脚本明确判定缺位即失败）。

set -euo pipefail

expected_count=0
found_count=0
for bin in "$@"; do
    expected_count=$((expected_count + 1))
    if [ ! -f "$bin" ]; then
        echo "FAIL: expected packaged binary NOT FOUND: $bin" >&2
        echo "  (any missing expected artifact means packaging is incomplete -> fail-closed)" >&2
        exit 1
    fi
    if ! head -c 4 "$bin" | grep -q $'\x7fELF'; then
        echo "FAIL: $bin exists but is not an ELF binary" >&2
        exit 1
    fi
    found_count=$((found_count + 1))
    echo "PASS: $bin present and is a valid ELF binary"

    # R34: 包内 CLI 实际执行（失败可观测）
    if [ "$(basename "$bin")" = "monitor-sensor" ]; then
        if out=$("$bin" --help 2>&1); rc=$?; then :; fi
        if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "Usage:"; then
            echo "PASS: monitor-sensor --help executed (exit $rc) and printed usage"
        elif [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
            # 跨编译 worker 无法执行 aarch64；ELF 校验已通过，但不虚报"执行成功"
            echo "NOTE: monitor-sensor cannot be executed on this host (rc=$rc, cross-compile worker?) — ELF presence verified, execution not runnable here"
        else
            echo "FAIL: monitor-sensor --help exited $rc or no usage output" >&2
            exit 1
        fi
    fi
done

if [ "$expected_count" -eq 0 ]; then
    echo "FAIL: no expected binaries were passed to the check" >&2
    exit 1
fi
if [ "$found_count" -ne "$expected_count" ]; then
    echo "FAIL: expected $expected_count packaged artifacts but only found $found_count" >&2
    exit 1
fi

echo "iio-sensor test_package: ALL $expected_count expected packaged artifacts present and verified (fail-closed, R03)"