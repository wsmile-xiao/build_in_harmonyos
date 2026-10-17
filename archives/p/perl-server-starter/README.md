# perl-server-starter

A superdaemon for hot-deploying server programs (Server::Starter).

## 简介

Server::Starter 是一个热部署超级守护进程（superdaemon），它通过 prefork + 套接字传递机制实现服务程序的无停机重启。
当需要重启服务时，`start_server` 会启动新进程，将监听套接字传递给新进程，待新进程就绪后优雅关闭旧进程。

核心特性：
- **热部署**: 服务程序可在不中断连接的情况下重启
- **套接字传递**: 通过环境变量 `SERVER_STARTER_PORT` 传递监听套接字
- **信号管理**: 支持 HUP（热重启）、TERM（终止）等信号
- **Guard 模块**: `Server::Starter::Guard` 提供守护进程式管理

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.35-r4 | published | 2026-06-29 |

## 构建系统

- **类型**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **编译方式**: 源码仅含 Build.PL (Module::Build)，在 conanfile.py 中动态生成 Makefile.PL
- **纯 Perl 模块**: 无 XS 代码，无原生编译

## 鸿蒙适配

- **平台**: OpenHarmony 6.0 (aarch64)
- **Perl**: 5.42.0
- **无需源码补丁**: conanfile.py 内含运行时适配（Makefile.PL 生成 + start_server 自定位补丁）
- **无 XS 依赖**: 不受鸿蒙 .so 加载限制影响
- **Conan 引用**: `perl-server-starter/0.35-r4@ohpcd/stable`

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/start_server` | 热部署超级守护进程脚本 |
| `lib/perl5/Server/Starter.pm` | Server::Starter 核心模块 |
| `lib/perl5/Server/Starter/Guard.pm` | Server::Starter::Guard 守护模块 |

## 使用示例

```perl
# 在服务程序中使用 Server::Starter
use Server::Starter;

# start_server 脚本会设置环境变量传递套接字
# 服务程序只需从环境变量获取套接字 fd
my $port = $ENV{SERVER_STARTER_PORT} || '';
# 格式: port=fd, 如 8080=3
```

```bash
# 启动服务（热部署模式）
start_server --port 8080 -- perl /path/to/server.pl

# 热重启（发送 HUP 信号）
kill -HUP $(cat /path/to/start_server.pid)

# 终止服务
kill -TERM $(cat /path/to/start_server.pid)
```

## 依赖

- perl 5.008+
- 无第三方编译依赖（纯 Perl 模块）

## 参考经验

编译过程参考了 perl-dbd-pg 的编译经验：
- Module::Build 不可用时动态生成 Makefile.PL
- package() 使用 os.walk+shutil.copy2 替代 conan copy()
- package_info() 通过 runenv_info 设置 PERL5LIB
