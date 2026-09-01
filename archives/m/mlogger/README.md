# mlogger

## 简介

mlogger 是一个命令行 syslog 日志工具，fork 自 bsdutils `logger`，由
Nathan Brown 维护（nbrownus/mlogger）。主要增强：

- 支持 64KB 超长日志行（原 logger 受限于 1KB；上限可改 `MAX_LINE` 常量）
- 缩进行续接（`-I <ms>`）：以空格/tab 开头的行被视为前一行的延续，超时后落盘
- 支持本地 syslog（默认 TCP）、UDP 远程 syslog（`-n`/`-d`）、Unix socket（`-u`）

## 功能概述

```
mlogger [options] [message]

Options:
 -d, --udp              use UDP (TCP is default)
 -i, --id               log the process ID too
 -f, --file <file>      log the contents of this file
 -h, --help             display this help text and exit
 -n, --server <name>    write to this remote syslog server
 -P, --port <number>    use this UDP port
 -p, --priority <prio>  mark given message with this priority
 -s, --stderr           output message to standard error as well
 -t, --tag <tag>        mark every line with this tag
 -u, --socket <socket>  write to this Unix socket
 -I, --indent <ms>      consider indented lines continuation, within timeout
 -V, --version          output version information and exit
```

## OHOS 适配

- 上游为单文件 C 程序（mlogger.c，556 行），仅依赖 POSIX/sys/socket/getopt/
  err.h/syslog.h 等标准头文件，HarmonyOS PC（AArch64 musl + libc++）下原生
  编译通过，**零 patch**。
- 配方忠实于上游 Makefile 的编译命令（`cc -Wall -Wextra -O3 -o mlogger mlogger.c`），
  仅将 `gcc` 替换为 Conan conf 提供的 OHOS clang（R33）。
- 上游无测试套件（无 tests/ 目录、Makefile 无 test/check 目标、无 CTest/CI）。
- `--version` 输出 `mlogger 1.1.2`：上游 `PROGRAM_VERSION` 常量硬编码为
  `"1.1.2"`，未随 v1.2.0 tag 更新——这是真实上游行为，测试据此断言。

## 依赖关系

- 编译依赖：无（仅需 clang，单文件 C，链接 libc）
- 运行依赖：系统 syslog 守护进程（OHOS 默认环境具备）或 `-s` 输出到 stderr

## 参考资料

- 官网/源码: https://github.com/nbrownus/mlogger
- License: BSD-4-Clause-UC（见源码头与 debian/copyright）
