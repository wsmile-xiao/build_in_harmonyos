# perl-proc-forksafe

**Proc::ForkSafe** — 帮助对象在 fork 后保持安全的 Perl 模块

## 基本信息

| 项 | 值 |
|------|------|
| 软件名 | perl-proc-forksafe |
| 版本 | 0.001 |
| 许可证 | Artistic-1.0-Perl OR GPL-1.0-or-later |
| 主页 | https://github.com/skaji/perl-Proc-ForkSafe |
| 构建系统 | ExtUtils::MakeMaker (perl-eumm) |
| 平台 | OpenHarmony (aarch64) |
| 状态 | ✅ published |

## 描述

Proc::ForkSafe 提供了一种机制，使 Perl 对象在 fork() 后自动重新初始化。

模块提供两个核心方法：
- **wrap($new, $destroy)** — 包装一个对象构造器，返回 ForkSafe 包装对象。可选提供 destroy 回调。
- **call($method, @args)** — 调用包装对象的方法。如果在子进程中（PID 变化），先销毁旧对象再重新创建。

典型用途：持久 TCP 连接、数据库连接等需要在 fork 后重新建立的对象。

## 依赖

| 依赖 | 最低版本 | 实际版本 |
|------|---------|---------|
| perl | 5.008001 | 5.42.0 |

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.001 | published | 2026-06-26 |