# GNU Coreutils for HarmonyOS/OpenHarmony

## 概述
GNU Coreutils 是 GNU 项目的基础工具集，包含文件、文本和 Shell 操作的核心命令。

## 版本
| 版本 | 状态 | 二进制数 | 备注 |
|------|------|---------|------|
| 9.10 | ✅ success | 86 | 排除14个不兼容命令 |

## 排除命令 (14个)
- **SELinux 软链接限制 (12个)**: ls, rm, cp, mv, stat, chmod, chown, chgrp, ln, link, unlink, realpath, readlink
- **系统兼容性 (2个)**: chroot (syscall 不支持), tac (double-free 边界 case)

## 替代方案
排除的命令应使用 HarmonyOS 内置的 **toybox** 版本。

## 补丁
- 0001: HarmonyOS 系统检测支持
- 0002: fstat/lseek EACCES 降级处理
- 0003: od.c fstat EACCES 修复 (补丁2遗漏)

## 详细文档
各版本的完整编译记录、测试报告和技术细节请查看对应版本目录下的 `README.md`。
