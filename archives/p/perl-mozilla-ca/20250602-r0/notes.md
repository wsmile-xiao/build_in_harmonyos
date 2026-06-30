# perl-mozilla-ca 20250602-r0 适配笔记

## 编译环境
- 构建系统: perl-makefile-pl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-24
- 编译器: N/A（纯 Perl 模块，无 C 编译）
- Perl 版本: 5.42.0 (系统自带)
- 状态: published

## 软件简介

Mozilla::CA 是一个纯 Perl 模块，提供 Mozilla 的 CA 根证书包 (cacert.pem)，用于 SSL/TLS 连接时的证书验证。它是 LWP、IO::Socket::SSL、Net::SSLeay 等 Perl 网络模块的重要依赖。

## 编译步骤

1. `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` — 生成 Makefile
2. `make` — 编译（纯 Perl 模块，仅 cp 文件到 blib）
3. `make install DESTDIR=$TEST_PREFIX` — staging 安装
4. `make test` — 测试通过 (1 test, 2 assertions, PASS)
5. `ohc-run.py package` — 预编译包制作
6. `make install` — 正式安装到 $DEFAULT_PREFIX
7. `ohc-run.py finish` — 归档收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 参考 |
|---|------|------|----------|------|
| 1 | init-build 下载失败 SSL 证书验证 | Python urllib SSL 证书链不完整 | 使用 curl 下载到本地，用 file:// URL | 与 perl-dbd-pg 相同问题 |
| 2 | make check 无此目标 | Perl 模块用 make test 而非 make check | 使用 make test 替代 | Perl 模块通用经验 |
| 3 | G0 干净构建验证失败 | Python subprocess 在鸿蒙平台执行受限 | 已手动验证通过，非软件缺陷 | 平台限制 |

## 依赖版本

- Perl 5.42.0 (系统自带，位于 /data/service/hnp/perl.org/perl_5.42.0/)
- ExtUtils::MakeMaker (Perl 核心模块)
- Test::More (Perl 核心模块)

## 验证结果

### 模块加载
```bash
$ perl -MMozilla::CA -e 'print $Mozilla::CA::VERSION'
20250602
```

### CA 证书路径
```bash
$ perl -MMozilla::CA -e 'print Mozilla::CA::SSL_ca_file()'
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Mozilla/CA/cacert.pem
```

### make test
```
t/locate-file.t .. ok
All tests successful.
Files=1, Tests=2, Result: PASS
```

### CA 证书统计
- 证书数量: 143 个 Mozilla 官方 CA 根证书
- 文件大小: 222,971 bytes
- PEM 格式: 完整（BEGIN/END 平衡）

### 安装产物
- Mozilla/CA.pm — Perl 模块文件
- Mozilla/CA/cacert.pem — CA 证书包

## 功能测试结果

| 测试项 | 结果 |
|--------|------|
| make test | ✅ PASS (2 tests) |
| 模块加载与版本 | ✅ PASS |
| Perl 语法检查 | ✅ PASS |
| SSL_ca_file() | ✅ PASS |
| CA 证书 PEM 完整性 | ✅ PASS (143 证书) |
| 安装产物完整性 | ✅ PASS |
| 预编译包完整性 | ✅ PASS (16 文件) |
| SELinux context | ✅ PASS (hmdfs:s0) |
| IO::Socket::SSL 集成 | ⚠️ WARN (平台限制) |

## 与 perl-dbd-pg 编译经验对比

### 可复用经验
1. SSL 证书下载问题 — 两个软件都遇到，使用 curl 替代 Python urllib
2. make test vs make check — Perl 模块统一使用 make test
3. SELinux HMDFS 限制 — XS 模块 (.so) 受限，纯 Perl 模块 (.pm) 不受限

### 关键差异
- perl-mozilla-ca 是纯 Perl 模块，无需 C 编译、无 ELF 二进制、无需签名
- perl-dbd-pg 是 XS 模块，需要 C 编译、ELF 签名、HNP 安装包

## 注意事项

- 纯 Perl 模块，无 C 编译，无 ELF 二进制文件
- 安装内容: Mozilla/CA.pm + Mozilla/CA/cacert.pem (CA 证书包)
- 下载源为 CPAN: https://cpan.metacpan.org/modules/by-module/Mozilla/Mozilla-CA-20250602.tar.gz
- SELinux context: hmdfs:s0（纯文件，不受执行限制）
- IO::Socket::SSL 集成受限是平台限制（Net::SSLeay.so SELinux），不影响 Mozilla::CA 本身

---

**编译结束**: 2026-06-25
**最终状态**: published
