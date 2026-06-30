#! /data/service/hnp/bin/bash
# OpenHarmony/HMDFS 编译修复脚本 - E011 umask 修复
sed -i 's/umask 077/umask 022/g' configure
echo "✅ E011 umask fix applied"
