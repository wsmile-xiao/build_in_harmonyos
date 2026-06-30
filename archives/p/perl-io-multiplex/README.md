# perl-io-multiplex

Perl IO::Multiplex 模块 - 管理多个 IO 流的单回调处理器

## 描述

IO::Multiplex 是一个纯 Perl 模块，用于管理多个 IO 流（如套接字、管道等），通过单个回调函数处理所有流的读写事件。适用于网络服务器、代理程序等需要同时处理多个连接的场景。

## 特性

- 纯 Perl 实现，无需 XS 编译
- 支持多路复用（select/poll 模式）
- 单回调函数管理多个 IO 流
- 支持读/写/异常事件处理

## 编译状态

| 版本 | 状态 | 编译日期 | 测试结果 | 预编译包 | 说明 |
|------|------|---------|---------|---------|------|
| 1.16 | built | 2026-06-12 | ✅ PASS (32/32) | ✅ 39KB | 纯 Perl 模块，质量门禁通过 |

### 测试详情

- **测试套件**: 4 个测试文件
- **总测试数**: 32
- **通过数**: 32
- **失败数**: 0
- **耗时**: 16 wallclock secs

### 质量门禁

- ✅ G1: 二进制完整性
- ✅ G2: 功能可用性
- ✅ G3: 可移植性
- ✅ G4: 档案完整性

## 依赖

- Perl 5.42.0+
- IO::Socket（核心模块）

## 使用限制

XS 模块（如 IO.so）在 HMDFS 上无法加载，受鸿蒙 SELinux 安全限制。需要管理员安装到系统目录 `/data/service/hnp/` 才能正常使用。

## 安装

```bash
# 设置 PERL5LIB 环境变量
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0

# 使用模块
perl -MIO::Multiplex -e 'print "OK\n"'
```

## 相关链接

- CPAN: https://metacpan.org/pod/IO::Multiplex
- 作者: Bruce J Keeler, Rob Brown (BBB)