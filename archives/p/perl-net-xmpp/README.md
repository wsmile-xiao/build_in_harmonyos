# perl-net-xmpp

> XMPP (Extensible Messaging and Presence Protocol) support library for Perl

## 软件描述

Net::XMPP 是一个 Perl 模块，提供 XMPP (可扩展消息和存在协议) 的支持库。XMPP 是一种基于 XML 的开放式即时通讯协议标准，广泛应用于即时消息、Presence 信息和协商式请求/响应服务。

该模块提供了完整的 XMPP 客户端实现，包括：
- 连接管理 (Connection, Client)
- 消息收发 (Message)
- 在线状态管理 (Presence)
- 信息/查询 (IQ)
- 花名册管理 (Roster)
- 隐私列表 (PrivacyLists)
- JID 解析 (JID)
- XML Stanza 处理 (Stanza)
- 协议实现 (Protocol)
- 命名空间定义 (Namespaces)
- 调试支持 (Debug)

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.05-r0 | ✅ published | 2026-06-29 | 纯 Perl 模块，OpenHarmony 平台直接可用 |

## 使用说明

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-net-xmpp/1.05-r0@ohpcd/stable

# 或通过 Perl 直接安装
perl Makefile.PL
make
make install
```

### 基本用法

```perl
use Net::XMPP;

# 创建 JID
my $jid = Net::XMPP::JID->new("user@example.com/resource");
print $jid->GetUserID();   # user
print $jid->GetServer();   # example.com
print $jid->GetResource(); # resource

# 创建消息
my $msg = Net::XMPP::Message->new();
$msg->SetMessage(
    to   => "recipient@example.com",
    from => "sender@example.com",
    type => "chat",
    body => "Hello World"
);
print $msg->GetXML();

# 创建客户端
my $client = Net::XMPP::Client->new();
# $client->Connect(hostname => "xmpp.example.com", ...);
```

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| XML::Stream | 1.24 | 运行时 |
| Authen::SASL | 2.2000 | 运行时 |
| Digest::SHA | 6.04 | 运行时 |
| MIME::Base64 | 3.16_01 | 运行时 |

## 平台兼容性

- ✅ OpenHarmony (aarch64-linux-ohos) — 完全兼容
- ✅ Linux (aarch64) — 兼容
- 纯 Perl 模块，不受 SELinux HMDFS 限制影响

## 已知限制

1. **XML::Stream 警告**: 运行时会产生 "Possible precedence problem between ! and numeric eq (==)" 警告，来自上游 XML::Stream 1.24 模块，不影响功能。
2. **网络测试**: t/gtalk.t 和 t/srv.t 需要网络连接或额外测试依赖，离线环境中会跳过或失败。
3. **隐私列表/花名册实例化**: PrivacyLists 和 Roster 模块需要活动 XMPP 连接才能实例化，离线测试仅验证模块加载。
