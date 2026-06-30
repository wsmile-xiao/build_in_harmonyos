# perl-mail-imapclient

Perl IMAP 客户端模块，提供完整的 IMAP4rev1 协议支持。

## 描述

Mail::IMAPClient 是一个 Perl 模块，用于与 IMAP 服务器交互。它提供了完整的 IMAP4rev1 协议实现，支持：

- 邮箱管理（创建、删除、重命名）
- 邀请函处理
- 消息操作（获取、复制、移动、删除）
- 邮箱搜索和排序
- ACL 支持
- QUOTA 支持
- IDLE 支持

## 版本信息

- **当前版本**: 3.43
- **发布日期**: 2023-08-15
- **CPAN**: https://metacpan.org/dist/Mail-IMAPClient

## 鸿蒙平台适配

### 编译状态
- ✅ 编译成功
- ✅ 测试通过 (109 tests, 3 skipped)
- ✅ 预编译包可用

### 平台限制
- ⚠️ XS 模块需要安装到系统目录（SELinux HMDFS 限制）
- ⚠️ 需要安装可选依赖才能使用完整功能：
  - Authen::NTLM（NTLM 认证）
  - Authen::SASL（SASL 认证）
  - IO::Socket::SSL（SSL/TLS 连接）

### 已测试功能
- ✅ 消息集解析
- ✅ BODYSTRUCTURE 解析
- ✅ fetch_hash 功能
- ✅ 线程处理

### 跳过测试
- ⏭️ basic.t（需要 IMAP 服务器连接）
- ⏭️ quota.t（需要 IMAP 服务器连接）
- ⏭️ pod.t（需要 Test::Pod 模块）

## 使用方法

```perl
use Mail::IMAPClient;

# 连接 IMAP 服务器
my $imap = Mail::IMAPClient->new(
    Server   => 'imap.example.com',
    User     => 'username',
    Password => 'password',
    SSL      => 1,
) or die "Cannot connect: $@";

# 选择邮箱
$imap->select('INBOX') or die "Cannot select INBOX: $@";

# 搜索消息
my @msgs = $imap->search('ALL');
print "Found " . scalar(@msgs) . " messages\n";

# 获取消息摘要
for my $msg (@msgs) {
    my $subject = $imap->parse_headers($msg, 'Subject');
    print "Subject: $subject\n";
}

# 断开连接
$imap->logout();
```

## 依赖

### 必需依赖
- perl >= 5.10
- perl-io-socket-ip（网络连接）

### 可选依赖
- Authen::NTLM（NTLM 认证）
- Authen::SASL（SASL 认证）
- Digest::HMAC（DIGEST-MD5 认证）
- IO::Socket::SSL（SSL/TLS 连接）

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mail-imapclient 3.43
```

## 相关模块

- perl-mail-dkim（DKIM 签名验证）
- perl-mail-spf（SPF 记录验证）
- perl-mailtools（邮件处理工具）

## 许可证

Artistic License 2.0