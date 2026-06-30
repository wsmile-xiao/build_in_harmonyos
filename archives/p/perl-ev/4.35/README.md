# EV 后端对比与选择指南

## 版本说明

perl-ev 4.35 提供两个版本：

| 版本 | HNP 包 | 后端配置 | 适用场景 |
|------|--------|----------|----------|
| **通用版** | perl-ev-4.35-ohos-aarch64.hnp (64KB) | select only | 少量连接、简单应用 |
| **高性能版** | perl-ev-4.35-epoll-ohos-aarch64.hnp (67KB) | epoll + select + inotify | 高并发、服务端应用 |

## 后端对比

### select 后端（通用版）

**优点**：
- ✅ 最通用，所有 POSIX 系统都支持
- ✅ 编译简单，无依赖
- ✅ 小文件，占用内存少

**限制**：
- ❌ 最多 1024 个文件描述符
- ❌ O(n) 性能，大量连接时效率下降
- ❌ 每次调用重传所有 FD
- ❌ 只支持水平触发

### epoll 后端（高性能版）

**优点**：
- ✅ 无 FD 数量限制（系统级上限）
- ✅ O(1) 性能，高并发表现优秀
- ✅ 增量注册，无需每次重传
- ✅ 支持水平触发和边缘触发
- ✅ inotify 支持高效文件监控
- ✅ eventfd/signalfd 支持高效信号处理

**适用场景**：
- Web 服务器、API 服务
- 实时消息系统
- 大量客户端连接
- 高并发异步 I/O

## 性能对比

| 连接数 | select 性能 | epoll 性能 |
|--------|-------------|------------|
| < 100 | 🟢 足够 | 🟢 足够 |
| 100-500 | 🟡 可接受 | 🟢 优秀 |
| 500-1000 | 🟠 较慢 | 🟢 优秀 |
| > 1000 | 🔴 瓶颈 | 🟢 优秀 |
| > 10000 | 🔴 无法工作 | 🟢 优秀 |

## 编译方法

### 通用版（默认）
```bash
export PERL_MM_USE_DEFAULT=1
export PERL_CANARY_STABILITY_NOPROMPT=1
perl Makefile.PL
make
```

### 高性能版（epoll）
```bash
export PERL_MM_USE_DEFAULT=1
export PERL_CANARY_STABILITY_NOPROMPT=1
export EV_EPOLL=1
export EV_INOTIFY=1
export EV_EVENTFD=1
export EV_SIGNALFD=1
perl Makefile.PL
make
```

## 安装建议

| 应用类型 | 推荐版本 |
|----------|----------|
| 命令行脚本、工具 | 通用版 |
| Web 服务、API 服务 | 高性能版 |
| 实时通信服务 | 高性能版 |
| 后台守护进程 | 高性能版 |
| 一次性脚本 | 通用版 |

## 安装方法

管理员选择合适的版本安装：

```bash
# 通用版
sudo -u installs unzip perl-ev-4.35-ohos-aarch64.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/

# 高性能版
sudo -u installs unzip perl-ev-4.35-epoll-ohos-aarch64.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/
```

## 后端选择（运行时）

EV 会在运行时自动选择最优后端，优先级：

```
高性能版: epoll > select
通用版:   select (唯一可用)
```

可通过 `EV::backend()` 查看当前后端：

```perl
use EV;
print "Backend: ", EV::backend(), "\n";
# 高性能版输出: Backend: epoll
# 通用版输出:   Backend: select
```

## 环境变量控制

可通过 `LIBEV_FLAGS` 强制指定后端：

| LIBEV_FLAGS | 使用的后端 |
|-------------|-----------|
| 1 | select |
| 2 | poll (未编译) |
| 4 | epoll |
| 8 | kqueue (未编译) |
| 64 | linuxaio (未编译) |
| 128 | io_uring (未编译) |

示例：
```bash
# 强制使用 select（即使有 epoll）
export LIBEV_FLAGS=1
perl your_script.pl

# 强制使用 epoll
export LIBEV_FLAGS=4
perl your_script.pl
```