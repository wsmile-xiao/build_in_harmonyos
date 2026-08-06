#!/usr/bin/env sh
set -eu

# acccheck test_package 测试脚本
# 用法: test.sh <acccheck.pl 完整路径>
# acccheck 是纯 Perl 脚本，架构无关；逻辑测试在构建机（CI runner）上运行，
# 无条件执行（can_run 守卫会在 OHOS 交叉编译时跳过测试并触发 L1e 误判，
# gsan/fcheck 先例）。

acccheck=${1:?acccheck.pl path is required}

# 产物存在性检查
if [ ! -f "$acccheck" ]; then
    echo "FAIL: acccheck.pl not found at $acccheck" >&2
    exit 1
fi
echo "PASS: acccheck.pl exists at $acccheck"

# Perl 解释器可用性检查
if ! command -v perl >/dev/null 2>&1; then
    echo "FAIL: perl interpreter not found on build host" >&2
    exit 1
fi

# 执行 acccheck.pl（无参数运行时输出用法帮助）
perl "$acccheck"
echo "PASS: acccheck.pl executed successfully"
