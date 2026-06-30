# LWP::UserAgent::Determined

## 简介

LWP::UserAgent::Determined 是 LWP::UserAgent 的扩展模块，提供了智能的 HTTP 请求重试机制和速率限制功能。它能够在遇到失败请求时自动重试，并根据响应状态码调整请求频率，非常适合需要稳定HTTP通信的应用场景。

## 功能概述

- **自动重试机制**：当 HTTP 请求失败时自动重试，支持配置重试次数和间隔
- **速率限制**：根据服务器响应状态码（如 429 Too Many Requests）自动调整请求频率
- **智能等待**：基于响应头中的 Retry-After 字段计算等待时间
- **继承 LWP::UserAgent**：完全兼容 LWP::UserAgent 的所有功能

## OHOS 适配

### 适配要点

1. **纯 Perl 模块**：本模块为纯 Perl 实现，无 XS 代码，不依赖特定平台，可直接在 OpenHarmony 上运行
2. **依赖关系**：依赖 perl-libwww（LWP::UserAgent）、perl-http-message 和 perl-uri
3. **构建系统**：使用标准的 Perl Makefile.PL 构建系统
4. **测试兼容**：所有测试用例在 OpenHarmony 平台正常通过

### 已知问题

无已知问题。该模块完全兼容 OpenHarmony 平台。

### 与 Linux 的差异

无差异。本模块为纯 Perl 实现，行为在所有平台上一致。

## 依赖关系

### 编译依赖

- perl（5.42.0）
- perl-libwww（LWP::UserAgent）
- perl-http-message
- perl-uri

### 运行依赖

- perl（5.42.0）
- perl-libwww（LWP::UserAgent）
- perl-http-message
- perl-uri

## 使用示例

```perl
use LWP::UserAgent::Determined;

# 创建用户代理
my $ua = LWP::UserAgent::Determined->new;

# 配置重试策略
$ua->timeout(10);
$ua->env_proxy;

# 发送请求（失败时自动重试）
my $response = $ua->get('http://example.com/api/data');

if ($response->is_success) {
    print $response->decoded_content;
} else {
    die $response->status_line;
}
```

## 参考资料

- [CPAN: LWP::UserAgent::Determined](https://metacpan.org/pod/LWP::UserAgent::Determined)
- [GitHub: LWP-UserAgent-Determined](https://github.com/sburke/LWP-UserAgent-Determined)