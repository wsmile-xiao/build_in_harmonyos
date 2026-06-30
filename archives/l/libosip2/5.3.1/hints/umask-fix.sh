#!/bin/bash
# E011: 修改 configure 中的 umask 077 为 umask 022
# HMDFS 文件系统的 UID 映射导致 umask 077 创建的临时目录无法写入
sed -i 's/umask 077/umask 022/g' configure
