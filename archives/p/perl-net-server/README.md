# perl-net-server (Net::Server)

Net::Server 是一个可扩展的 Perl 网络服务器框架，提供多种服务器类型（Fork、PreFork、PreForkSimple、HTTP、PSGI 等），支持 TCP/UDP/UNIX 套接字、SSL 加密、多路复用等特性。

## 功能概述

- **多种服务器模型**: Fork、PreFork、PreForkSimple、Single、MultiType、Multiplex、Thread、HTTP、PSGI
- **多协议支持**: TCP、UDP、UNIX Domain Socket、UNIX Datagram、SSL/SSLEAY
- **日志系统**: Sys::Syslog、Log::Log4perl
- **进程管理**: Daemonize（后台运行）、SIG 信号处理
- **PSGI 支持**: 可作为 PSGI 应用服务器

## OHOS 适配

Net::Server 是纯 Perl 模块，无 C/XS 编译，在 OpenHarmony 平台上无需特殊适配：

- 构建系统: `perl Makefile.PL` + `make` + `make install`
- 所有核心依赖均为 Perl 核心模块（File::Temp、IO::Socket、POSIX、Socket、Time::HiRes）
- 无需补丁、无需平台特异代码
- 可选功能（Thread/Multiplex/SSL/SSLEAY）依赖外部 Perl 模块，缺失不影响核心功能

### 已知限制

| 功能 | 状态 | 原因 |
|------|------|------|
| Net::Server::Thread | ⚠️ 需 threads 模块 | Perl 未编译线程支持 |
| Net::Server::Multiplex | ⚠️ 需 IO::Multiplex | 可选依赖未安装 |
| Net::Server::Proto::SSL | ⚠️ 需 IO::Socket::SSL | 可选 SSL 模块未安装 |
| Net::Server::Proto::SSLEAY | ⚠️ 需 Net::SSLeay | 可选 SSL 模块未安装 |

> 以上限制均为可选功能缺失，不影响 Net::Server 的核心服务器功能。

## 依赖关系

### 编译依赖
- Perl 5.42.0（系统自带）

### 运行依赖
- Perl 5.42.0
- 核心模块（File::Temp、IO::Socket、POSIX、Socket、Time::HiRes）— Perl 自带

### 可选依赖
- IO::Multiplex — 用于 Multiplex 服务器
- threads — 用于 Thread 服务器
- IO::Socket::SSL / Net::SSLeay — 用于 SSL 加密

## 参考资料

- [CPAN - Net::Server](https://metacpan.org/dist/Net-Server)
- [Net::Server 文档](https://metacpan.org/pod/Net::Server)
