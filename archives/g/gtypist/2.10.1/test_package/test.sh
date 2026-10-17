#!/bin/sh
# gtypist 2.10.1 消费者行为测试源文件（与 conanfile.py test() 同源，由其调用执行）
# 断言：包内 gtypist 二进制（gengetopt 命令行）在 OHOS 上真实可执行且行为正确
set -e

# 1) --version 输出版本号并退出 0（证明二进制可执行且 gengetopt 命令行正常）
gtypist --version | grep -q "2.10.1"

# 2) --help 输出用法（退出码 0）
gtypist --help > /dev/null

# 3) 反向：非法长选项必须以非零退出码结束（gengetopt 标准行为）。
# 显式判断而非 set -e + ! 组合——POSIX 2.8.1 规定 ! 管道不触发 errexit，
# 隐式写法会让本断言永远不可能失败（AI 评审 P2 指出）。
if gtypist --no-such-option-xyz > /dev/null 2>&1; then
    echo "FAIL: invalid long option should be rejected" >&2
    exit 1
fi

echo "consumer test passed: 3/3 assertions"
