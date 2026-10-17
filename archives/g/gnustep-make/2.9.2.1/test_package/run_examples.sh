#!/bin/sh
# run_examples.sh — 运行上游 GNUstep TestFramework 的 9 个 example
#
# 由 test_package/conanfile.py 的 test() 调用。example1-9 已在 build 阶段
# 由 CMake 编译为可执行文件（testing/exampleX.m，从上游 TestFramework/ 原样
# 复制，未修改）。本脚本逐个真实运行，全部 9 个必须 EXIT 0，否则判红。
#
# 说明：example3/4 是上游故意设计的异常测试（向 NSString 发送坏消息测异常
# 捕获，其内部会记录一个预期的 "Failed test" 断言），在完整 GNUstep 环境
# （依赖已发布的 gnustep-base/1.31.1 + libc++_shared.so 注入）下异常被
# NS_DURING/NS_HANDLER 正常捕获，程序正常退出（EXIT 0）——实测 9/9 全过。
#
# 环境变量：
#   EXE_DIR       example 可执行文件所在目录（必填）
#   SDK_CXX_LIB   OHOS SDK C++ 运行时目录（含 libc++_shared.so，可选）

set -u

if [ -z "${EXE_DIR:-}" ]; then
    echo "ERROR: EXE_DIR not set" >&2
    exit 1
fi

# libobjc.so 依赖 libc++_shared.so（OHOS SDK 提供），需加入运行时搜索路径
if [ -n "${SDK_CXX_LIB:-}" ]; then
    export LD_LIBRARY_PATH="${SDK_CXX_LIB}:${LD_LIBRARY_PATH:-}"
fi

failures=""

for i in 1 2 3 4 5 6 7 8 9; do
    "${EXE_DIR}/example${i}"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "example${i}: PASS"
    else
        echo "example${i}: FAIL (rc=${rc})"
        failures="${failures} example${i}(rc=${rc})"
    fi
done

# 鸿蒙特有测试：验证 HarmonyOS PC 适配配置（7 项断言，详见 test_ohos_config.c）
"${EXE_DIR}/test_ohos_config"
rc=$?
if [ "$rc" -ne 0 ]; then
    failures="${failures} test_ohos_config(rc=${rc})"
fi

if [ -n "$failures" ]; then
    echo "ERROR: upstream example tests failed:${failures}" >&2
    exit 1
fi

echo "upstream TestFramework examples: 9 built & run (9/9 PASS, EXIT 0) + OHOS config test: 7 assertions PASS"
exit 0
