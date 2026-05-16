# userspace-rcu

## 软件简介
userspace-rcu 是一个用户空间 RCU (Read-Copy-Update) 库，提供了高效的并发数据访问机制。RCU 是一种同步机制，允许读取者无锁访问共享数据，同时写入者可以安全地更新数据。

## 官方资源
- **网站**: http://liburcu.org/
- **源码**: https://github.com/urcu/userspace-rcu
- **License**: LGPL-2.1-or-later AND MIT

## 已编译版本
| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.15.6 | Partial | 2026-05-08 | HMDFS 临时目录问题，使用 out-of-tree 构建 |

## 核心功能
- **liburcu**: RCU 基础库
- **liburcu-qsbr**: Quiescent State Based Reclamation
- **liburcu-mb**: Memory Barrier RCU flavor
- **liburcu-memb**: Explicit memory barrier flavor
- **liburcu-bp**: Bulletproof RCU (自动注册读取者)
- **liburcu-cds**: 并发数据结构 (队列、栈、哈希表等)

## 典型应用
- LTTng tracing 系统
- 高并发数据库
- 低延迟通信系统
- 内核追踪工具

## HongMeng 平台编译注意事项
由于 HMDFS 文件系统的特殊限制，autotools 构建系统需要特殊处理：
1. 使用 out-of-tree 构建模式
2. 修改 configure 临时目录创建逻辑 (umask 002)
3. 创建 .config-tmp 子目录规避权限问题

详见各版本目录下的 patches/ 和 PROGRESS.md