#!/bin/sh
# gnuit 4.9.5 消费者行为测试源文件（与 conanfile.py test() 同源，由其调用执行）
# 断言：包内 gitwhich 二进制（PATH 查找工具）在 OHOS 上真实可执行且行为正确
set -e

# 1) 正向：找到包内 gitfm（编译产物真实存在、可执行、PATH 集成正确）
gitwhich gitfm

# 2) 正向：找到包内 gitwhich 自身
gitwhich gitwhich

# 3) 反向：查不存在的程序必须以非零退出码结束（用 sh 的 '!' 归零整个命令）
! gitwhich no-such-gnuit-tool-xyz

echo "consumer test passed: 3/3 assertions"
