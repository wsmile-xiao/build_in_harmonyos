# sersniff

sersniff 是一个在**两个串口（或 TCP）端口之间转发数据并实时显示收发内容**的串口嗅探/隧道工具。

## 功能概述

- 在两个串口端口间建立隧道，同时把数据流打印到终端
- 支持 TCP：`-i :port` 监听端口、`-o host:port` 连接远端
- 命令行选项：`-b` 波特率、`-s` 静默（不转发只显示）、`-n` 不做端口配置、
  `-x` 十六进制显示、`-f` 十六进制打印格式、`-w` 延迟报告阈值等
- 附带 `sersniff.8` 手册页

## OHOS 适配

- **构建**：纯 Makefile（无 configure、无 install target）。Makefile 硬编码
  `CC = gcc` 且 `LINK = gcc`（最终链接用 `$(LINK)`），OHOS 无 gcc，需从 Conan
  `tools.build:compiler_executables:c` 取 clang 并在 `make` 命令行同时覆盖
  `CC` 与 `LINK`（R33）。
- **安装**：无 `install` 目标，`package()` 手动把二进制拷到 `bin/`、man8 页拷到
  `share/man/man8/`、LICENSE 拷到 `licenses/`。
- **测试**：上游无任何测试框架（Makefile 仅 `all`/`clean`，无 `check` 目标、无
  `tests/` 目录）。test_package 以真实二进制做 CLI 冒烟测试（`-h` 版本横幅、
  `-h` 用法帮助、`-b` 非法波特率拒绝），无需串口/网络硬件。
- **与 Linux 差异**：`usage()` 的帮助/非法参数分支 `exit(1)`（非 0），调用方须以
  输出内容而非退出码判断。

## 依赖关系

- 编译依赖：无（仅 libc）
- 运行依赖：无（仅 libc + POSIX sockets/termios）

## 参考资料

- 官网：http://www.earth.li/projectpurple/progs/sersniff.html
- 源码归档：https://www.earth.li/projectpurple/files/sersniff-0.0.5.tar.gz
