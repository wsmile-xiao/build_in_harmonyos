# perl-iptables-parse 1.6.1-r4 适配笔记

## 编译环境
- 构建系统: perl（Makefile.PL）
- 编译日期: 2026-06-11
- 编译器: 无（纯 Perl 模块，无 XS 代码）
- 状态: built

## 编译步骤

1. 下载源码：从 CPAN 获取 IPTables-Parse-1.6.1.tar.gz
   - URL: https://cpan.metacpan.org/authors/id/M/MR/MRASH/IPTables-Parse-1.6.1.tar.gz
   - SHA512: 7638665e34f06771519bc8989ad57b6308c5efb39ecb32f3f6f208d0ece1675f...

2. 解压源码：tar -xzf IPTables-Parse-1.6.1.tar.gz

3. 生成 Makefile：perl Makefile.PL INSTALLDIRS=vendor
   - 出现 mandir 未初始化警告（ExtUtils::MM_Unix.pm），不影响构建

4. 编译：make（纯 Perl 模块，仅复制 .pm 文件）

5. 测试：make test
   - 测试结果：PASS（1 test, 1 file）

6. 安装：手动安装到 staging 目录
   - 目标路径：$DEFAULT_PREFIX/lib/perl5/site_perl/IPTables/Parse.pm

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Savannah 下载站点证书问题 | 使用 CPAN 镜像（cpan.metacpan.org） |
| 2 | 初始 URL 返回 404 | 脚本搜索的 URL 不正确 | 从 Alpine APKBUILD 获取正确 URL |
| 3 | INSTALLVENDORLIB 为空 | Perl 5.42.0 vendor 路径配置问题 | 手动安装到 site_perl 目录 |

## 源码修改

无需补丁，纯 Perl 模块直接可用。

## 依赖版本

- perl 5.42.0（预装）
- ExtUtils::MakeMaker（Perl 核心模块）

## 验证结果

```bash
make test
# 输出: All tests successful.
# Files=1, Tests=1
# Result: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Parse.pm | ~4KB | Perl 模块主文件 |

## 注意事项

1. 这是纯 Perl 模块（noarch），无 XS 代码，无需 ELF 签名
2. 安装路径应为 Perl 的 site_perl 或 vendor_perl 目录
3. 需要确保 Perl 环境能正确找到模块路径
---

**编译结束**: 2026-06-12 10:20
**最终状态**: published
