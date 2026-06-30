# perl-net-async-http 0.50-r0 适配笔记

## 编译环境
- 构建系统: Module::Build (Perl)
- 编译日期: 2026-06-24
- 编译器: clang 18.1.8 (aarch64-unknown-linux-ohos)
- Perl: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 下载源码: `Net-Async-HTTP-0.50.tar.gz` (CPAN)
2. 解压到构建目录
3. 配置: `perl Build.PL --install_base=$DEFAULT_PREFIX`
4. 编译: `./Build`
5. 测试: `./Build test` (556 项通过, 0 失败, 5 跳过)
6. Staging 安装: `./Build install --destdir=$TEST_PREFIX`
7. 预编译包制作: `ohc-run.py package`
8. 本地安装: `./Build install` (安装到 ~/usr/local)
9. 功能测试: 模块加载、对象创建、异步 HTTP 请求验证
10. 收尾: `ohc-run.py finish`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无编译问题 | 纯 Perl 模块，无 XS 组件 | 直接编译通过 |

### 跳过的测试项说明

| 测试文件 | 原因 | 影响 |
|---------|------|------|
| t/21local-connect-ssl.t | 缺少 IO::Async::SSL | SSL 功能不可用，不影响 HTTP |
| t/24local-connect-redir-ssl.t | 缺少 IO::Async::SSL | SSL 重定向不可用 |
| t/40socks.t | 缺少 Net::Async::SOCKS | SOCKS 代理不可用 |
| t/81cross-https.t | 缺少 IO::Async::SSL | HTTPS 测试不可用 |
| t/99pod.t | 缺少 Test::Pod | POD 文档检查跳过 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时/编译时 |
| IO::Async | 0.805 | 运行时 |
| HTTP::Message | 6.46 | 运行时 |
| HTTP::Cookies | 6.11 | 运行时 |
| URI | 5.21 | 运行时 |
| Module::Build | 0.4234 | 编译时 |
| Test::Metrics::Any | 0.01 | 测试时 |

## 验证结果

```bash
# 模块加载验证
$ perl -MNet::Async::HTTP -e 'print $Net::Async::HTTP::VERSION, "\n"'
0.50

# 对象创建验证
$ perl -e 'use Net::Async::HTTP; use IO::Async::Loop; my $loop = IO::Async::Loop->new(); my $http = Net::Async::HTTP->new(); $loop->add($http); print "OK\n";'
OK

# 异步 HTTP 请求验证（本地服务器）
# 发送 GET 请求到本地 HTTP 服务器
# 结果: HTTP 200, body="Hello World!" ✅

# API 方法验证
$ perl -e 'use Net::Async::HTTP; my $h = Net::Async::HTTP->new(); print join(", ", grep { $h->can($_) } qw(do_request GET POST PUT HEAD DELETE)), "\n";'
do_request, GET, POST, PUT, HEAD, DELETE
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-net-async-http-0.50-r0-ohos-aarch64.tar.gz | 71,201 bytes | 预编译包（纯 Perl） |

## 注意事项

1. **纯 Perl 模块**: 无 XS 组件，不存在 SELinux/HMDFS 限制问题（与 perl-dbd-pg 不同）
2. **可选依赖**: SSL（IO::Async::SSL）和 SOCKS（Net::Async::SOCKS）功能需额外安装对应模块
3. **构建系统**: 使用 Module::Build 而非 ExtUtils::MakeMaker，构建命令为 `./Build` 而非 `make`
4. **安装路径**: 模块安装到 `~/usr/local/lib/perl5/Net/Async/HTTP.pm` 及子目录
5. **无补丁**: 源码无需任何修改即可在鸿蒙平台编译通过

---

**编译结束**: 2026-06-24 17:49
**最终状态**: published
