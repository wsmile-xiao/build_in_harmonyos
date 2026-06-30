#!/bin/bash
# 自动化处理 libhtp 源码包
cd "$1"
autoreconf -i -f -v
sed -i 's/umask 077/umask 022/g' configure