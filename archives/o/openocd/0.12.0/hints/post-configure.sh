#!/bin/sh
# 修复 config.status 临时目录创建问题
# 在 HarmonyOS 上，mktemp -d "./confXXXXXX" 可能因权限问题失败

if [ -f config.status ]; then
    # 统一临时目录路径（TMPDIR 未设置或不可写时回退 /tmp）
    TMP_DIR="${TMPDIR:-/tmp}/openocd-config-tmp"
    mkdir -p "$TMP_DIR" 2>/dev/null || {
        TMP_DIR=/tmp/openocd-config-tmp
        mkdir -p "$TMP_DIR"
    }

    # 修改 config.status 使用固定的临时目录
    sed -i "s|tmp=\`(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null\`|tmp=${TMP_DIR}/conf\$\$-\$RANDOM|g" config.status
    sed -i "s|tmp=./conf\$\$-\$RANDOM|tmp=${TMP_DIR}/conf\$\$-\$RANDOM|g" config.status
fi
