# checkbashisms — 检查 shell 脚本中的 bash 特定语法

## 概述

checkbashisms 是 Debian devscripts 包中的 Perl 脚本，用于检查
/bin/sh 脚本中是否使用了 bash 特有的语法（bashisms），
帮助编写兼容 POSIX sh 的脚本。

## 版本

- 上游版本: 2.25.28
- 许可证: GPL-2.0
- 上游 URL: https://salsa.debian.org/debian/devscripts

## 构建说明

- 类型: Perl 脚本（无需编译）
- 构建系统: 手动（替换版本号 + 设置权限）
- 编译器: 不适用
- 目标平台: OHOS aarch64

## 功能

- `checkbashisms` — 检查脚本中的 bashisms
- `checkbashisms -p` — 启用额外可移植性检查
- `checkbashisms -f` — 只检查脚本文件（不检查 stdin）
- `checkbashisms -x` — 显示额外调试信息