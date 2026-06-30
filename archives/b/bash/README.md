# GNU Bash — OpenHarmony 编译档案

## 软件简介
GNU Bash 是标准的 Unix shell，提供命令行交互和脚本编程功能。

## 功能概述
- 命令行交互
- 脚本编程（变量、函数、数组、算术运算）
- 管道和重定向
- 命令替换
- 作业控制

## OHOS 适配要点
- 修改 config.guess/config.sub 添加 HarmonyOS 识别（`__OHOS__` 宏）
- 使用 `--without-bash-malloc` 禁用内置内存分配器
- 使用 bundled readline（>= 8.3），不使用 --with-installed-readline
- NEEDED 仅 libc.so，ncurses/readline 静态嵌入（R4 合规）

## 依赖关系
- 可选依赖: ncurses（静态链接）
- 使用 bundled readline

## 参考资料
- [GNU Bash 官方文档](https://www.gnu.org/software/bash/manual/)
- [GNU FTP](https://ftp.gnu.org/gnu/bash/)

## conan