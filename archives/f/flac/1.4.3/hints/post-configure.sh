#!/bin/sh
# 修复 config.status 临时目录创建问题
# 在 HarmonyOS 上，mktemp -d "./confXXXXXX" 可能因权限问题失败

if [ -f config.status ]; then
    # 创建专用的临时目录
    mkdir -p $TMPDIR/flac-config-tmp 2>/dev/null || mkdir -p /tmp/flac-config-tmp
    
    # 修改 config.status 使用固定的临时目录
    sed -i 's|tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`|tmp=$TMPDIR/flac-config-tmp/conf$$-$RANDOM|g' config.status
    sed -i 's|tmp=./conf$$-$RANDOM|tmp=$TMPDIR/flac-config-tmp/conf$$-$RANDOM|g' config.status
fi
