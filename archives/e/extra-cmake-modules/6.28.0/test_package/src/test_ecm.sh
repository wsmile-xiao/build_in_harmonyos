#!/bin/sh
# test_ecm.sh — ECM test script.
# R34: test_package 必须实质调用被测包的 API/CMake 模块。
# ECM 是 cmake-only 模块包，"调用 ECM API" = find_package(ECM) 并使用其 cmake 宏。
# 此脚本验证 CMake configure 阶段生成的 ecm_verified 标记文件的内容，
# 确保所有断言均通过。
set -euo pipefail

if [ ! -f "ecm_verified" ]; then
    echo "ERROR: ecm_verified marker file not found — CMake configure did not verify ECM modules"
    exit 1
fi

# 校验断言数量：应等于 core(5) + kde(4) + includes(4) + dirs(2) = 15
expected_assertions=15
actual=$(grep "^ecm_verified=" ecm_verified | cut -d= -f2)
if [ "$actual" -ne "$expected_assertions" ]; then
    echo "ERROR: Expected ${expected_assertions} assertions, got ${actual}"
    cat ecm_verified
    exit 1
fi

# 校验各分类断言数量
core=$(grep "^core_modules_checked=" ecm_verified | cut -d= -f2)
kde=$(grep "^kde_modules_checked=" ecm_verified | cut -d= -f2)
inc=$(grep "^includes_checked=" ecm_verified | cut -d= -f2)
dir=$(grep "^directories_checked=" ecm_verified | cut -d= -f2)

if [ "$core" -ne 5 ]; then
    echo "ERROR: Expected 5 core modules checked, got ${core}"
    exit 1
fi
if [ "$kde" -ne 4 ]; then
    echo "ERROR: Expected 4 KDE modules checked, got ${kde}"
    exit 1
fi
if [ "$inc" -ne 4 ]; then
    echo "ERROR: Expected 4 includes checked, got ${inc}"
    exit 1
fi
if [ "$dir" -ne 2 ]; then
    echo "ERROR: Expected 2 directories checked, got ${dir}"
    exit 1
fi

cat ecm_verified
echo "ECM test_package verification: ${actual}/${expected_assertions} assertions passed"
