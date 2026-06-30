# Net::Telnet

Net::Telnet 是一个 Perl 模块，用于与 TELNET 端口或其他 TCP 端口进行交互。它提供了面向对象的接口，支持 TELNET 协议协商、命令执行、数据收发等功能。

## 功能概述

- **TELNET 协议支持**：完整的 TELNET 协议实现，包括选项协商
- **TCP 连接**：可作为通用 TCP 客户端使用（`Telnetmode => 0`）
- **命令执行**：通过 `cmd()` 方法远程执行命令并获取输出
- **模式匹配**：通过 `waitfor()` 等待特定输出模式
- **日志功能**：支持 input_log 和 dump_log 用于调试
- **错误处理**：支持 die、return、回调三种错误模式
- **纯 Perl 实现**：无 XS 依赖，无 C 编译要求

## OHOS 适配

### 适配要点

- **零修改编译**：纯 Perl 模块，无需任何源码补丁或修改
- **构建系统**：使用 Perl ExtUtils::MakeMaker（`Makefile.PL`）
- **CPAN 下载**：Savannah URL 已失效，需从 CPAN 下载源码
- **SSL 证书**：鸿蒙平台 SSL 证书链不完整，下载时需 `curl -kL`
- **mkfifo 警告**：`make -j2` 时出现 mkfifo 警告，非致命，编译正常完成

### 与 Linux 的差异

| 方面 | Linux | OHOS |
|------|-------|------|
| 下载 | wget/curl | curl -kL（SSL 证书链不完整） |
| mkfifo | 支持 | 不支持（警告但非致命） |
| SELinux | 通常无限制 | 纯 Perl 模块不受影响 |
| 临时目录 | /tmp | $TMPDIR 或 $HOME/tmp |

### 已知问题

无。纯 Perl 模块在鸿蒙平台完全兼容。

## 依赖关系

- **编译依赖**：Perl 5.42.0+，ExtUtils::MakeMaker（系统自带）
- **运行依赖**：Perl 5.42.0+
- **外部依赖**：无

## 参考资料

- 官网：https://metacpan.org/dist/Net-Telnet
- CPAN 下载：https://cpan.metacpan.org/authors/id/J/JR/JROGERS/Net-Telnet-3.05.tar.gz
- 文档：https://metacpan.org/pod/Net::Telnet
