# perl-net-async-http-server

Perl module for serving HTTP requests asynchronously using IO::Async.

## 描述

Net::Async::HTTP::Server 是一个基于 IO::Async 的异步 HTTP 服务器模块。它允许 Perl 程序在事件驱动的模式下处理 HTTP 请求，支持 PSGI 接口和 Plack Handler。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.15-r0 | published | 2026-06-24 | 纯Perl模块，鸿蒙平台完全可用 |

## 构建系统

- **类型**: Perl (Module::Build)
- **配置**: `perl Build.PL --install_base=$DEFAULT_PREFIX`
- **编译**: `./Build`
- **测试**: `./Build test`
- **安装**: `./Build install`

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| perl | 5.42.0 | 系统预装 |
| Module::Build | 0.4234 | 系统预装 |
| IO::Async | 0.805 | CPAN手动安装 |
| HTTP::Request | 系统版本 | 系统预装 |
| HTTP::Response | 系统版本 | 系统预装 |
| Metrics::Any | 0.10 | 系统预装 |
| Future | 0.52 | 系统预装 |
| Future::Utils | 0.52 | 系统预装 |
| Struct::Dumb | 0.16 | 系统预装 |

## 鸿蒙平台特性

- ✅ **纯Perl模块**：无C/XS组件，不受SELinux HMDFS限制
- ✅ **完全可用**：14项功能测试全部通过
- ✅ **无补丁需求**：源码无需修改即可编译
- ⚠️ **SSL证书**：下载时需使用 `curl --insecure`（系统CA证书问题）

## 使用示例

```perl
use Net::Async::HTTP::Server;
use IO::Async::Loop;
use HTTP::Response;

my $loop = IO::Async::Loop->new();

my $server = Net::Async::HTTP::Server->new(
   on_request => sub {
      my $self = shift;
      my ( $req ) = @_;

      my $response = HTTP::Response->new( 200 );
      $response->add_content( "Hello, OpenHarmony!" );
      $response->content_type( 'text/plain' );
      $req->respond( $response );
   },
);

$loop->add( $server );

$server->listen(
   addr => { family => "inet", socktype => "stream", port => 8080 },
)->get;

$loop->run;
```
