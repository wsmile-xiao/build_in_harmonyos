# perl-net-jabber

Perl module for accessing the Jabber/XMPP protocol.

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.0-r0 | published | 2026-06-26 | 纯 Perl 模块，鸿蒙平台适配完成 |

## 描述

Net::Jabber 提供 Jabber/XMPP 协议的 Perl 接口，支持消息发送、在线状态管理、IQ 请求/响应、JID 解析等功能。

## 依赖

- Perl >= 5.18
- Net::XMPP >= 1.0
- XML::Stream >= 1.0

## 构建

```bash
perl Makefile.PL && make && make install
```

## 使用

```perl
use Net::Jabber;

my $msg = Net::Jabber::Message->new();
$msg->SetMessage(to => 'user@example.com', body => 'Hello');
print $msg->GetXML();
```

## 许可证

LGPL-2.1
