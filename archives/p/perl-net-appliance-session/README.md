# perl-net-appliance-session

Perl 模块 Net::Appliance::Session — 用于与网络设备（路由器、交换机等）进行 CLI 交互会话。

## 描述

Net::Appliance::Session 提供了一个简洁的 API，用于通过 SSH、Telnet 或 Serial 连接到网络设备并执行命令。它基于 Net::CLI::Interact 构建，支持多种设备类型（personality）的 phrasebook。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 4.300005-r5 | published | 2026-06-24 |

## 使用说明

### 基本用法

```perl
use Net::Appliance::Session;

my $s = Net::Appliance::Session->new(
    personality => "cisco",
    transport   => "SSH",
    host        => "192.168.1.1",
    username    => "admin",
    password    => "password",
);

$s->connect();
$s->begin_privileged("privileged_password");

my $output = $s->cmd("show version");
print $output;

$s->end_privileged();
$s->close();
```

### CLI 工具

```bash
# 交互式连接
nas -p cisco -t SSH -u admin 192.168.1.1

# 录制会话
nas -p cisco -R -s session.script 192.168.1.1

# 回放会话
nas -p cisco -P session.script 192.168.1.1
```

## 鸿蒙平台说明

### 可用功能

- ✅ 模块加载和 API 调用
- ✅ Session 对象创建和参数验证
- ✅ 命令构建和 phrasebook 解析
- ✅ Async 异步会话模块
- ✅ CLI 工具 (nas)
- ✅ 会话录制/回放

### 平台限制

- ⚠️ **SSH/Telnet 交互连接**: 需要 IO::Tty (XS 模块)，受 SELinux HMDFS 限制
  - 根因: `hishell_hap` SELinux domain 只能加载 `hnp_file` 类型的 `.so` 文件
  - 解决方案: 将 IO::Tty 安装到系统目录 `/data/service/hnp/`，参考 HNP 包安装流程

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| perl | 5.42.0 | 运行时 |
| Net::CLI::Interact | 2.300003 | 运行时 |
| IO::Prompt::Tiny | 0.003 | 运行时 |
| Term::ReadPassword | 0.11 | 运行时 |
| Module::Build | 0.42+ | 构建 |

## 源码

- URL: https://cpan.metacpan.org/authors/id/O/OL/OLIVER/Net-Appliance-Session-4.300005.tar.gz
- 许可证: perl (Artistic/GPL)
