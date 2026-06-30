# perl-net-async-xmpp 0.003-r0 适配笔记

## 编译环境
- 构建系统: makefile (Perl ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-25
- 编译器: N/A (纯 Perl 模块，无需 C/C++ 编译器)
- Perl: v5.42.0 (aarch64-linux), 路径 /data/service/hnp/bin/perl
- 安装前缀: /storage/Users/currentUser/usr/local
- 状态: built

## 编译步骤

Net::Async::XMPP 0.003 是纯 Perl 模块，使用 Dist::Zilla 生成的 Makefile.PL 构建。

```bash
# 1. 解压源码
tar xzf Net-Async-XMPP-0.003.tar.gz
cd Net-Async-XMPP-0.003

# 2. 生成 Makefile
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local

# 3. 编译 (纯 Perl，仅复制 .pm 文件到 blib/)
make -j1

# 4. 安装
make install

# 5. 验证
perl -MNet::Async::XMPP -e 'print $Net::Async::XMPP::VERSION'
# 输出: 0.003
```

编译过程无需任何补丁，Makefile.PL 开箱即用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `perl Makefile.PL` 成功，`make` 成功，但 `make test` 中 2/4 编译测试失败 | Client.pm 和 Protocol.pm 通过传递依赖链加载 Net::SSLeay (XS .so)，受 SELinux HMDFS 限制无法加载 | 平台限制，非编译缺陷。需将 XS 依赖安装到系统目录 (hnp_file 标签) |
| 2 | Protocol::XMPP 加载失败，缺 XML::LibXML::SAX::ChunkParser | XML::LibXML 是 XS 模块，同样受 SELinux 限制 | 同上，需管理员安装到系统目录 |
| 3 | CPAN 依赖安装时 `cpan` 命令超时 | OpenHarmony 网络环境限制 | 手动从 cpan.metacpan.org 下载 tarball，本地 `perl Makefile.PL && make && make install` |
| 4 | XML::SAX 安装后 XML::SAX::Base 缺失 | XML::SAX 和 XML::SAX::Base 是独立分发 | 手动下载安装 XML-SAX-Base-1.09.tar.gz |

## 依赖版本

### 运行时依赖 (META.yml)

| 模块 | 要求版本 | 已安装版本 | 状态 |
|------|---------|-----------|------|
| Future | 0.29 | 系统自带 | ✅ |
| Future::Utils | 0.29 | 已安装 | ✅ |
| IO::Async | 0.60 | 已安装 | ✅ |
| IO::Async::SSL | 0.14 | 0.23 | ✅ (但传递依赖 Net::SSLeay 受限) |
| IO::Async::Resolver::DNS | 0.04 | 0.06 | ✅ |
| Mixin::Event::Dispatch | 1.000 | 已安装 | ✅ |
| Protocol::XMPP | 0.006 | 0.006 | ✅ (但传递依赖 XML::LibXML 受限) |
| Socket | 2.000 | 系统自带 | ✅ |
| curry | 任意 | 2.000001 | ✅ |
| parent | 任意 | 0.244 | ✅ |

### 测试依赖

| 模块 | 要求版本 | 已安装版本 | 状态 |
|------|---------|-----------|------|
| Test::More | 0.98 | 1.302210 | ✅ |
| Test::Fatal | 0.010 | 0.017 | ✅ |
| Test::CheckDeps | 0.010 | 0.010 | ✅ |

### 受 SELinux 限制的 XS 依赖

| XS 模块 | .so 文件路径 | SELinux 标签 | 加载状态 |
|---------|-------------|-------------|---------|
| Net::SSLeay | ~/usr/local/lib/.../auto/Net/SSLeay/SSLeay.so | hmdfs:s0 | ❌ Permission denied |
| XML::LibXML | ~/usr/local/lib/.../auto/XML/LibXML/LibXML.so | hmdfs:s0 | ❌ Permission denied |

## 验证结果

### 编译验证

```bash
$ perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
Checking if your kit is complete...
Looks good
Generating a Unix-style Makefile

$ make -j1
cp lib/Net/Async/XMPP/Server.pm blib/lib/Net/Async/XMPP/Server.pm
cp lib/Net/Async/XMPP/Client.pod blib/lib/Net/Async/XMPP/Client.pod
cp lib/Net/Async/XMPP.pm blib/lib/Net/Async/XMPP.pm
cp lib/Net/Async/XMPP/Client.pm blib/lib/Net/Async/XMPP/Client.pm
cp lib/Net/Async/XMPP/Protocol.pm blib/lib/Net/Async/XMPP/Protocol.pm
cp lib/Net/Async/XMPP/Protocol.pod blib/lib/Net/Async/XMPP/Protocol.pod

$ make install
# 6 个文件安装到 ~/usr/local/lib/site_perl/5.42.0/Net/Async/
```

### 模块加载验证

```bash
$ perl -MNet::Async::XMPP -e 'print $Net::Async::XMPP::VERSION'
0.003                                          # ✅ 主模块加载成功

$ perl -MNet::Async::XMPP::Server -e 'print "OK"'
OK                                             # ✅ Server 模块加载成功

$ perl -MNet::Async::XMPP::Client -e 'print "OK"'
# ❌ 失败: Client → Protocol → IO::Async::SSL → Net::SSLeay (XS) → Permission denied

$ perl -MNet::Async::XMPP::Protocol -e 'print "OK"'
# ❌ 失败: Protocol → IO::Async::SSL → Net::SSLeay (XS) → Permission denied
```

### 测试套件结果

```bash
$ make test
t/00-check-deps.t ............. ok             # ✅ 依赖检查通过
t/00-compile.t ................
  Failed 2/4 subtests                         # ❌ Client.pm 和 Protocol.pm 编译失败
t/000-report-versions-tiny.t .. ok             # ✅ 版本报告通过
Result: FAIL
Failed 1/3 test programs. 2/23 subtests failed.
```

### 语法检查

```bash
$ perl -c lib/Net/Async/XMPP.pm       # syntax OK ✅
$ perl -c lib/Net/Async/XMPP/Server.pm # syntax OK ✅
$ perl -c lib/Net/Async/XMPP/Client.pm # BEGIN failed ❌ (SSL XS 依赖链)
$ perl -c lib/Net/Async/XMPP/Protocol.pm # BEGIN failed ❌ (SSL XS 依赖链)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Net/Async/XMPP.pm | 1.6KB | 主模块 |
| Net/Async/XMPP/Client.pm | 4.0KB | 客户端实现 |
| Net/Async/XMPP/Client.pod | 1.8KB | 客户端文档 |
| Net/Async/XMPP/Protocol.pm | 7.5KB | 协议实现 |
| Net/Async/XMPP/Protocol.pod | 1.5KB | 协议文档 |
| Net/Async/XMPP/Server.pm | 2.1KB | 服务器实现 |

## 注意事项

1. **SELinux HMDFS 限制**: 与 perl-dbd-pg 共享相同的平台限制。XS 模块 (.so 文件) 安装在 HMDFS 路径 (~/usr/local/) 下时，SELinux 标签为 `hmdfs:s0`，无法被 `hishell_hap` domain 的进程加载。需要管理员将 XS 依赖安装到系统目录 (`/data/service/hnp/`) 获取 `hnp_file:s0` 标签。

2. **无需补丁**: 与 perl-dbd-pg 不同，Net::Async::XMPP 是纯 Perl 模块，Makefile.PL 开箱即用，无需任何源码修改。

3. **运行时可用性**: 主模块和 Server 模块可立即使用。Client 和 Protocol 模块需要 XS 依赖 (Net::SSLeay, XML::LibXML) 安装到系统目录后才能使用。

4. **CPAN 安装策略**: `cpan` 命令在 OpenHarmony 上会超时。需手动从 `cpan.metacpan.org` 下载 tarball，使用 `fastapi.metacpan.org/v1/module/<Module>` API 获取正确的 author/dist/version 信息构造下载 URL。

---

**编译结束**: 2026-06-25 16:50
**最终状态**: built
