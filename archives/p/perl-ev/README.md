# perl-ev

## 描述

EV 是 libev 事件循环的 Perl 接口，提供高性能的事件驱动编程能力。支持 timer、I/O、signal、child、stat 等多种事件监控。

## 版本

当前编译版本：**4.35**

## OpenHarmony 适配状态

- ✅ 编译成功
- ⚠️ 运行时需管理员安装（SELinux HMDFS 限制）
- ✅ 提供通用版和高性能版

## 下载

| 版本 | 后端 | 适用场景 |
|------|------|----------|
| [通用版](4.35/packaging/perl-ev-4.35-ohos-aarch64.hnp) | select | 少量连接 |
| [高性能版](4.35/packaging/perl-ev-4.35-epoll-ohos-aarch64.hnp) | epoll | 高并发 |

## 安装

```bash
# 管理员安装
sudo -u installs unzip perl-ev-4.35-epoll-ohos-aarch64.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/
```

详细安装说明见 [4.35/README.md](4.35/README.md)

## 依赖

- common::sense >= 3.75

## 功能

| 功能 | 状态 |
|------|------|
| Timer 定时器 | ✅ |
| I/O 监控 | ✅ |
| Signal 处理 | ✅ |
| Child 进程监控 | ✅ |
| Stat 文件监控 | ✅ |
| Idle 回调 | ✅ |

## 后端性能

| 后端 | 连接上限 | 性能 |
|------|----------|------|
| select | 1024 | O(n) |
| epoll | 无限制 | O(1) |

推荐使用高性能版（epoll 后端）。