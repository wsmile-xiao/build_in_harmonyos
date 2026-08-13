# perl-crypt-eksblowfish

Crypt::Eksblowfish — Eksblowfish block cipher and bcrypt hashing for Perl.

## 软件信息

- **官网**: https://metacpan.org/dist/Crypt-Eksblowfish
- **源码**: https://cpan.metacpan.org/authors/id/Z/ZE/ZEFRAM/Crypt-Eksblowfish-0.009.tar.gz
- **许可证**: GPL-1.0-or-later OR Artistic-1.0
- **分类**: cryptography

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.009-r15 | built | 2026-07-03 | 首次编译成功，2026-07-09 CI 修复 (Module::Build→ExtUtils::MakeMaker) |

## 功能模块

- **Crypt::Eksblowfish** — Eksblowfish 块加密算法（XS 扩展）
- **Crypt::Eksblowfish::Bcrypt** — bcrypt 密码哈希
- **Crypt::Eksblowfish::Blowfish** — 标准 Blowfish 加密
- **Crypt::Eksblowfish::Family** — 密码族管理
- **Crypt::Eksblowfish::Subkeyed** — 子密钥支持
- **Crypt::Eksblowfish::Uklblowfish** — 无密钥 Blowfish

## 运行依赖

- perl (≥5.6)
- Class::Mix (≥0.001)
- MIME::Base64 (≥2.21)
- XSLoader

## 编译依赖

- OHOS SDK sysroot (musl C 库头文件)
- Module::Build (Perl 构建系统)
- ExtUtils::CBuilder (≥0.15, C 编译支持)

## 使用说明

Crypt::Eksblowfish 实现了 Eksblowfish 块加密算法，是 bcrypt 密码哈希算法的核心依赖。

### 安装

预编译包通过 Conan 安装：
```bash
conan install --requires=perl-crypt-eksblowfish/0.009-r15@ohpcd/stable
```

XS 模块 (.so) 需要安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/Eksblowfish/` 目录。

### 示例

```perl
use Crypt::Eksblowfish::Bcrypt qw(bcrypt);

# 生成 bcrypt 哈希
my $hash = bcrypt("password", '$2$05$' . 'a' x 22);
print "Hash: $hash\n";
```

### 注意事项

由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载。用户目录下的 .so 文件因安全上下文为 `hmdfs:s0`，会被 dlopen 拒绝加载。

---
*OpenHarmony 编译归档 · 2026-07-07*
