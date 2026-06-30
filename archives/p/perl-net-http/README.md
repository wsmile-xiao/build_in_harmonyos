# perl-net-http

## 软件描述

Net::HTTP 是一个低级 HTTP 连接客户端模块，提供 HTTP/1.1 协议支持。它是 LWP (Library for WWW in Perl) 的底层依赖，负责管理 HTTP 连接的生命周期、请求格式化和响应解析。

### 主要功能
- HTTP/1.1 协议支持（keep-alive、chunked 传输编码）
- HTTP 请求格式化（write_request）
- HTTP 响应解析（read_response_headers, read_entity_body）
- gzip/deflate 传输编码协商
- IPv4/IPv6 双栈支持（通过 IO::Socket::IP）
- HTTPS 支持（可选，依赖 Net::SSLeay）

### 模块类型
**纯 Perl 模块**（仅 .pm 文件，无 XS/.so），在 OpenHarmony 平台上直接编译可用，不受 SELinux HMDFS 限制影响。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 6.24-r0 | built | 2026-06-26 | Conan verify 全部通过，功能测试通过 |

## 使用说明

### 安装
```bash
# Conan 安装
conan install --requires=perl-net-http/6.24-r0@ohpcd/stable

# 或直接使用系统已安装版本
perl -MNet::HTTP -e 'print $Net::HTTP::VERSION'
```

### 基本用法
```perl
use Net::HTTP;

my $http = Net::HTTP->new(
    Host => "example.com",
    HTTPVersion => "1.1",
);

$http->write_request(GET => "/", Host => "example.com");
my ($code, $msg, %headers) = $http->read_response_headers;

my $body;
while (1) {
    my $n = $http->read_entity_body(my $buf, 4096);
    last unless $n;
    $body .= $buf;
}
```

### OpenHarmony 注意事项
- HTTP 功能完整可用
- HTTPS 不可用（Net::SSLeay XS 模块受 SELinux HMDFS 限制）
- 纯 Perl 模块，无需管理员安装或特殊配置

## 许可证

MIT
