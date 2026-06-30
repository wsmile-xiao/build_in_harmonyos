#!/bin/sh
# 修复 config.status 临时目录创建问题
# 在 HarmonyOS 上，umask 077 创建的临时目录权限过于严格，导致无法在其中创建文件

if [ -f config.status ]; then
    # 修改 config.status 的 umask 设置，从 077 改为 002
    sed -i 's/umask 077/umask 002/g' config.status
fi
