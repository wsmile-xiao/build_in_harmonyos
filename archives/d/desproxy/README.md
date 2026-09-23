# desproxy

## 是什么

desproxy 是一组命令行工具，用于将 TCP 流量隧道穿过 HTTP 代理（HTTP CONNECT 方法），
解决"只有 HTTP 代理出口却要跑 IRC / SSH / 其他 TCP 协议"的场景。

## 功能概述

| 工具 | 功能 |
|------|------|
| `desproxy` | 主程序：本地监听端口，把入站 TCP 连接经 HTTP 代理转发到远端主机 |
| `desproxy-inetd` | inetd 模式下的一次性转发 |
| `desproxy-socksserver` | 基于 desproxy 的 SOCKS5 服务器，可用 HTTP 代理作父代理 |
| `desproxy-dns` | DNS 转发器 |
| `socket2socket` | 把两个 socket 直接相连的微型工具 |

## OHOS 适配

- 纯 C 实现、无外部依赖（仅 libc + POSIX 头文件），autotools 构建。
- 老式 C 代码（1990s）在 `desproxy.h` 中直接定义全局变量（非 extern 声明），
  现代编译器（GCC≥10 / Clang）默认 `-fno-common` 会触发
  `multiple definition` 链接错误——配方通过 `AutotoolsToolchain.extra_cflags`
  注入 `-fcommon` 解决（构建参数层适配，无源码 patch）。
- 5 个二进制安装到 `bin/`，声明为命令行工具（commands.json，R38）。
- 上游无测试套件（Makefile 无 check/test 目标）；适配后补全消费者级冒烟测试
  （test_package 逐一执行 5 个二进制验证可运行与版本 banner）。

## 依赖关系

- 编译依赖：无
- 运行依赖：无（静态/动态链接由 Conan 管理）

## 参考资料

- 上游项目页：https://sourceforge.net/projects/desproxy/
- 源码包：`desproxy-0.1.0-pre3.tar.gz`（SourceForge，SHA256 d0c8a299...）
