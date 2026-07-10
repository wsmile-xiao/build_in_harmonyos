# perl-crypt-cast5

CAST5 block cipher for Perl (Crypt::CAST5).

## 软件信息

- **官网**: https://metacpan.org/dist/Crypt-CAST5
- **源码**: https://cpan.metacpan.org/authors/id/B/BO/BOBMATH/Crypt-CAST5-0.05.tar.gz
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: cryptography

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.05-r14 | built | 2026-07-02 | 首次编译成功，运行时受 hmmac 安全标签限制 |

## 运行依赖

- perl

## 编译依赖

- perl (Perl XS 开发头文件)
- clang (Harmonybrew OHOS LLVM)

## 使用说明

Crypt::CAST5 是 Perl 的 CAST5 分组密码模块，提供加密/解密功能。

### 安装

预编译包需安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/CAST5/` 目录。

### 注意事项

由于 hmmac 安全标签限制，XS 模块的 .so 需安装到系统目录 `/data/service/hnp` 才能被 dlopen 加载。详见功能测试报告。

---
*OpenHarmony 编译归档 · 2026-07-02*
