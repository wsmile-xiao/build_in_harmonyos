# gtimeout — GNU Coreutils timeout

gtimeout 是 GNU coreutils 中的 `timeout` 命令，加上 `g` 前缀以区分系统自带的 `timeout`。
它可以在限定时间内运行指定命令，超时后发送信号终止进程。

## 功能概述

- 在指定时长内运行命令，超时后终止
- 支持自定义终止信号 (--signal)
- 支持保留子进程退出状态 (--preserve-status)
- 支持发送信号后等待清理时间 (--kill-after)

## OHOS 适配

### 补丁说明
- **config.guess**: 添加 HarmonyOS 平台识别 (aarch64-unknown-linux-ohos)
- **freadahead.c**: 适配 musl libc 不透明 FILE 结构体
- **umask 077**: 修复 configure 中 HMDFS 兼容性问题

### 与 coreutils 9.10 对比
9.11 版本相比 9.10：
- 移除了 freadptr.c 和 freadseek.c，只需适配 freadahead.c
- timeout 命令不使用 fstat/lseek，无需 EACCES 补丁
- 源码格式从 tar.xz 变为 tar.gz

## 依赖关系

- Clang 编译器（HarmonyOS NDK）
- musl libc（系统自带）
- 无额外依赖

## 参考资料

- 官网: https://www.gnu.org/software/coreutils/
- 源码: https://ftp.gnu.org/gnu/coreutils/
