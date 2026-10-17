#!/bin/sh
# test_package/run_test.sh — POSIX sh 入口，调用 R-free 包树校验器（满足 L0c 的 .sh 测试源）
#
# 用法: ./run_test.sh <dir>
#   <dir> = 安装后的包目录（含 lib/R/library/boot/）或上游源码树根；
#   透传给 validate_boot.py，由其自动判定形态。
#
# 说明：CI 环境无 R 运行时，故此处以 Python 标准库实现的结构/数据校验替代
# 上游 R CMD check；本地自建 R 运行时的真实上游测试在 test_package/R/ 下
# （另由协作者子任务编写），不在本脚本范围内。
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec python3 "${SCRIPT_DIR}/validate_boot.py" "$@"
