# perl-crypt-bcrypt

Perl bcrypt 密码哈希模块 (Crypt::Bcrypt)，基于 crypt_blowfish C 库的 XS 扩展。

## 软件信息

- **官网**: https://metacpan.org/pod/Crypt::Bcrypt
- **源码**: https://github.com/Leont/crypt-bcrypt
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: security

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.011-r3 | built | 2026-07-02 | C 库功能验证通过 (16/16)，Perl XS 模块受平台 dlopen 限制不可用 |

## 运行依赖

- perl

## 编译依赖

- perl (ExtUtils::MakeMaker, ExtUtils::ParseXS — Perl core)
- clang

## 使用说明

Crypt::Bcrypt 是 Perl 的现代 bcrypt 密码哈希实现，包含 C XS 扩展 (Bcrypt.xs) 和 crypt_blowfish C 库。

### 平台限制

由于 OpenHarmony musl libc 的 `dlopen_config_abs_path_policy` 路径策略，从 HNP 启动的 Perl 无法 dlopen HMDFS 上的 .so。因此 `use Crypt::Bcrypt` 无法直接使用。

**建议使用方式**: 作为 C 库使用，通过 Conan 依赖引用，直接调用 `_crypt_blowfish_rn` 和 `_crypt_gensalt_blowfish_rn` 函数。C 库功能测试 16/16 全部通过。

详见: `0.011-r3/notes.md`

---
*OpenHarmony 编译归档 · 2026-07-02*
