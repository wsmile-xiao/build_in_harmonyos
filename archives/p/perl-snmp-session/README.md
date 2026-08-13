# perl-snmp-session

Perl SNMP Session 模块，提供 SNMP 协议访问功能。

## 软件信息

- **官网**: https://github.com/sleinen/snmp-session
- **源码**: https://github.com/sleinen/snmp-session
- **许可证**: Artistic-2.0
- **分类**: network

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.16-r2 | built | 2026-06-29 | 纯 Perl 模块，conan-verify 全部通过 |

## 运行依赖

- perl (>= 5.6.0)

## 可选依赖

- IO::Socket::INET6 (IPv6 支持)
- Net::SNMP (Net_SNMP_util.pm 需要)
- Socket6 (IPv6 支持)

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

SNMP::Session 是纯 Perl 实现的 SNMP 协议访问模块，支持 SNMPv1 和 SNMPv2c 协议。
包含以下核心模块：

| 模块 | 说明 |
|------|------|
| SNMP_Session.pm | 核心 SNMP 会话管理 (open, get, set, getnext, getbulk, trap) |
| BER.pm | BER (Basic Encoding Rules) 编解码 |
| SNMP_util.pm | SNMP 工具函数 (snmpget, snmpwalk, snmpset 等) |
| SNMP_Table.pm | SNMP 表格操作 |
| Net_SNMP_util.pm | 基于 Net::SNMP 的工具函数 (可选) |

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-snmp-session/1.16-r2
```

模块安装路径：`lib/perl5/`（Conan 包）或 `site_perl/5.42.0/`（系统安装）。

### 基本用法

```perl
use SNMP_Session;
use BER;

# 创建会话（需要 SNMP agent 运行）
my $session = SNMP_Session->open('127.0.0.1', 'public', 161);

# GET 请求
$session->get_request(encode_oid(1,3,6,1,2,1,1,1));

# 离线 BER 编码（不需要网络）
my $oid = encode_oid(1, 3, 6, 1, 2, 1, 1, 1);
my $encoded = encode_int(42);
my $pretty = pretty_print($encoded);
```

### 注意事项

- `encode_oid()` 接受列表参数 `(1,3,6,1)` 而非字符串 `"1.3.6.1"`
- `Net_SNMP_util.pm` 硬依赖 `Net::SNMP` 模块，未安装时无法加载（不影响其他模块）
- 纯 Perl 模块，无 C/XS 代码，无需 ELF 签名
- 前置依赖 (IO::Socket::INET6, Net::SNMP, Socket6) 为可选，不影响构建和基本功能

---
*OpenHarmony 编译归档 · 2026-06-29*
