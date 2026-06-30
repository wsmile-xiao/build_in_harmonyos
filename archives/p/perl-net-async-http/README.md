# Net::Async::HTTP

异步 HTTP 客户端 Perl 模块 — 鸿蒙平台预编译包

## 软件介绍

Net::Async::HTTP 是基于 IO::Async 的异步 HTTP/1.1 客户端模块，提供高性能的非阻塞 HTTP 请求能力。

### 主要特性
- 异步非阻塞 HTTP/1.1 客户端
- 连接池化与请求管线化（pipelining）
- 请求/响应流式处理
- Cookie 管理支持
- 超时与取消机制
- 重定向跟随
- 内容编码（gzip/deflate）支持
- 指标（Metrics::Any）集成

### 技术信息
- **版本**: 0.50-r0
- **许可证**: Perl Artistic License
- **构建系统**: Module::Build (Build.PL)
- **类型**: 纯 Perl 模块（无 XS 组件）
- **CPAN**: Net-Async-HTTP-0.50

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-24
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **编译器**: clang 18.1.8
- **Perl**: 5.42.0 (aarch64-linux)
- **状态**: ✅ 编译成功

### 平台适配说明
- 纯 Perl 模块，无需编译 XS 组件，不存在 SELinux/HMDFS 限制
- 使用 Module::Build 构建系统，`perl Build.PL --install_base=$DEFAULT_PREFIX`
- 所有 556 项测试通过（5 项因可选依赖缺失而跳过）
- 异步 HTTP 请求功能经本地服务器测试验证可用

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 纯 Perl 模块，无二进制文件 |
| G2 功能可用性 | PASS | 模块加载、对象创建、异步 HTTP 请求均通过 |
| G3 可移植性 | PASS | 纯 Perl，无 RPATH/签名问题 |
| G4 档案完整性 | PASS | 归档文件完整 |

## 使用方式

### 基本用法
```perl
use IO::Async::Loop;
use Net::Async::HTTP;

my $loop = IO::Async::Loop->new();
my $http = Net::Async::HTTP->new(
    user_agent => "MyApp/1.0",
    timeout => 30,
);
$loop->add($http);

$http->do_request(
    request => HTTP::Request->new(GET => "http://example.com/"),
    on_response => sub {
        my ($response) = @_;
        print $response->as_string;
    },
    on_error => sub {
        my ($message) = @_;
        print STDERR "Error: $message\n";
    },
);

$loop->run();
```

### Cookie 管理
```perl
use HTTP::Cookies;
my $jar = HTTP::Cookies->new();
my $http = Net::Async::HTTP->new(cookie_jar => $jar);
```

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| IO::Async | 0.805 | 运行时 |
| HTTP::Message | 6.46 | 运行时 |
| HTTP::Cookies | 6.11 | 运行时 |
| URI | 5.21 | 运行时 |
| Module::Build | 0.4234 | 编译时 |

## 跳过的测试项

以下测试因可选依赖未安装而跳过，不影响核心功能：
- `t/21local-connect-ssl.t` — 需要 IO::Async::SSL
- `t/24local-connect-redir-ssl.t` — 需要 IO::Async::SSL
- `t/40socks.t` — 需要 Net::Async::SOCKS
- `t/81cross-https.t` — 需要 IO::Async::SSL
- `t/99pod.t` — 需要 Test::Pod

## 安装

```bash
# 通过 cmd-pkgs 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-net-async-http 0.50-r0

# 验证安装
perl -MNet::Async::HTTP -e 'print $Net::Async::HTTP::VERSION, "\n"'
# 输出: 0.50
```
