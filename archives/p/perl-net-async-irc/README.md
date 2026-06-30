# perl-net-async-irc

Net::Async::IRC - Use IRC with IO::Async

## 描述

Net::Async::IRC 提供了一个基于 IO::Async 的 IRC 客户端协议实现。它封装了 IRC 协议的底层细节，包括消息解析、CTCP 协议支持、ISUPPORT 参数处理等，使开发者可以专注于 IRC 应用的业务逻辑。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.12-r0 | published | 2026-06-25 | 纯 Perl 模块，Conan 验证全通过 |

## 使用说明

### 环境要求

- Perl 5.14+
- IO::Async 0.54+
- Protocol::IRC 0.13+
- Future 0.43+
- Future::AsyncAwait 0.47+ (XS 模块，需系统安装)

### OpenHarmony 平台说明

1. **纯 Perl 模块**: Net::Async::IRC 本身是纯 Perl 实现，无 XS 组件。
2. **XS 依赖**: Future::AsyncAwait 和 XS::Parse::Sublike 是 XS 模块，受 SELinux HMDFS 限制，需安装到 `/data/service/hnp/` 系统目录。
3. **安装方式**: 通过 Conan 包安装 .pm 文件，XS 依赖需管理员安装。

### Conan 使用

```bash
# 安装包
conan install --requires=perl-net-async-irc/0.12-r0@ohpcd/stable

# 设置 PERL5LIB（注意：需同时包含系统 Perl 库路径）
export PERL5LIB="$CONAN_PACKAGE_DIR/lib:$(perl -e 'print join(":", grep {/site_perl/} @INC)')"
```

### 代码示例

```perl
use Net::Async::IRC;
use IO::Async::Loop;

my $loop = IO::Async::Loop->new;
my $irc = Net::Async::IRC->new;

$loop->add($irc);

$irc->login(nick => "MyNick", host => "irc.example.com")->get;
$irc->send_message("PRIVMSG", undef, "#channel", "Hello, world!");
```
