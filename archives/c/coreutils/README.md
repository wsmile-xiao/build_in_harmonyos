# GNU Coreutils

GNU Coreutils 是 GNU 项目的基础工具集，包含文件、文本和 Shell 操作的核心命令。

## 功能概述

- 文本处理：sort、cut、tr、uniq、head、tail、wc、cat、od 等
- 文件操作：touch、mkdir、rmdir、mkfifo、mknod、tee 等
- 系统信息：date、df、du、id、uname、whoami 等
- 目录/路径：basename、dirname、pwd、pathchk
- 进程控制：nice、nohup、timeout
- 其他：echo、env、sleep、seq、factor、shuf 等

## OHOS 适配

### 核心问题：fstat()/lseek() EACCES
HarmonyOS 对管道、终端、套接字的 fd 调用 fstat()/lseek() 返回 EACCES 错误，影响 cat、dd、head、sort、split、tail、wc、od 等命令。通过补丁添加 `#ifdef __OHOS__` 守卫，在 EACCES 时降级处理。

### 排除命令（14个）
因 SELinux 软链接限制或 syscall 不兼容，以下命令需使用系统 **toybox** 替代：
- **SELinux 限制（12个）**：ls、rm、cp、mv、stat、chmod、chown、chgrp、ln、link、unlink、readlink、realpath
- **syscall 不支持（2个）**：chroot（chroot syscall 不可用）、tac（>16KB 单行 double-free）

### 推荐安装策略
使用选择性安装脚本 `scripts/install-selected.sh`，只安装完全可用的 86 个命令。

## 依赖关系

- Clang 编译器（HarmonyOS NDK）
- musl libc（系统自带）
- 无额外依赖

## 参考资料

- 官网: https://www.gnu.org/software/coreutils/
- 源码: https://ftp.gnu.org/gnu/coreutils/
