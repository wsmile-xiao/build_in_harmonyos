# microsocks

多线程、小型、高效的 SOCKS5 服务器。

## 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | microsocks |
| 版本 | 1.0.5 |
| 许可证 | MIT |
| 语言 | C |
| 构建系统 | makefile |
| 源码URL | https://github.com/rofl0r/microsocks/archive/refs/tags/v1.0.5.tar.gz |

## 功能描述

MicroSocks 是一个轻量级 SOCKS5 代理服务器，特性包括：

- 多线程设计：每个客户端使用低栈大小的线程
- 支持 IPv4、IPv6、DNS
- 支持三种认证模式：无认证、用户名密码、一次性认证(auth_once)
- 资源耗尽时优雅拒绝新连接（不会 abort）
- 无配置文件，纯命令行参数驱动
- 静态链接 musl libc 时不到 50KB

## 支持的 SOCKS5 特性

- 认证：无认证(NO AUTH)、密码(USERNAME/PASSWORD)、一次性(AUTH_ONCE)
- 地址类型：IPv4、IPv6、域名(DNS)
- 协议：TCP（暂不支持 UDP）

## 命令行选项

```
microsocks -1 -q -i listenip -p port -u user -P passw -b bindaddr -w wl
```

| 选项 | 说明 |
|------|------|
| `-i listenip` | 监听IP地址（默认 0.0.0.0） |
| `-p port` | 监听端口（默认 1080） |
| `-u user` | 认证用户名（必须与 -P 一起使用） |
| `-P passw` | 认证密码（必须与 -u 一起使用） |
| `-b bindaddr` | 出站连接绑定IP |
| `-w ips` | 白名单IP（逗号分隔，免认证） |
| `-1` | 一次性认证模式：认证成功后IP自动加入白名单 |
| `-q` | 禁用日志输出 |

## 编译信息

| 属性 | 值 |
|------|-----|
| 编译日期 | 2026-06-03 |
| 编译器 | clang 15.0.4 |
| 目标平台 | OHOS aarch64 |
| 状态 | published |

## 依赖

无外部依赖。仅需要系统 libc 和 libpthread。

## 补丁

- `0001-configure.patch`: 为纯 Makefile 项目添加 configure wrapper，生成 config.mak（适配 G0 干净构建验证流程）

## 已发布版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.0.5 | published | 2026-06-03 |