# perl-net-jabber-bot

Automated Jabber Bot creation using Moose and Net::Jabber.

## 软件描述

Net::Jabber::Bot 是一个基于 Moose 和 Net::Jabber 的 Perl 模块，提供自动化 Jabber/XMPP 机器人创建功能。
支持消息收发、论坛管理、状态管理、联系人管理等功能。

这是一个**纯 Perl 模块**，无需 C/XS 编译，在 OpenHarmony 平台上开箱即用。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.1.7-r0 | published | 2026-06-26 | 纯 Perl 模块，全 Conan 验证通过 |

## 使用说明

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-net-jabber-bot/2.1.7-r0@ohpcd/stable

# 或直接使用已安装的 Perl
perl -MNet::Jabber::Bot -e 'print "OK\n"'
```

### 基本用法

```perl
use Net::Jabber::Bot;

my $bot = Net::Jabber::Bot->new({
    server          => 'jabber.example.com',
    conference_server => 'conference.jabber.example.com',
    port            => 5222,
    username        => 'mybot',
    password        => 'secret',
    alias           => 'MyBot',
    resource        => 'BotResource',
    message_function => \&handle_message,
});

$bot->Start();
```

### 平台兼容性

- ✅ OpenHarmony (aarch64) — 纯 Perl 模块，无 SELinux 限制
- ✅ 可从任意路径加载（不需安装到系统目录）
- ⚠️ StartParallel 模式需要 Parallel::ForkManager 模块

## 依赖

| 依赖 | 版本 | 必需 |
|------|------|------|
| Perl | 5.42.0 | ✅ |
| Net::Jabber | 2.0 | ✅ |
| Moose | 2.4000+ | ✅ |
| XML::Stream | 1.24+ | ✅ |
| LWP::UserAgent | 6.81+ | ✅ |
| Parallel::ForkManager | — | ⚠️ 可选 |
