# perl-scope-upper

**Scope::Upper** — Act on upper scopes (XS module)

## 简介

Scope::Upper 提供 Perl XS 接口，允许操作上层调用栈的作用域。支持 `reap`、`localize`、`localize_elem`、`unwind` 等函数，用于在当前子程序返回时执行代码或修改上层变量。

## 版本

- **当前版本**: 0.34
- **CPAN**: https://metacpan.org/dist/Scope-Upper
- **作者**: Vincent Pit (VPIT)

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | Perl XS (ExtUtils::MakeMaker) |
| 编译器 | clang 15 |
| 平台 | OpenHarmony 6.0 (aarch64) |
| Perl | 5.42.0 |
| 状态 | published |

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.34 | published | 2026-06-30 |

## 依赖

- Perl 5.42.0 (系统预装)
- clang (系统工具链)
- ExtUtils::MakeMaker (Perl 内置)

## 安装

```bash
# Conan 安装
conan install --requires=perl-scope-upper/0.34@ohpcd/stable

# 安装后需将 .so 复制到系统 perl site_perl 路径以解决 SELinux 限制
cp -a data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Scope/ \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Scope/
cp -a data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Scope/ \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Scope/
```

## 注意事项

- .so 在 conan 缓存路径 (hmdfs SELinux 上下文) 无法 dlopen，需安装到系统 perl 路径 (hnp_file 上下文)
- ELF 已使用 binary-sign-tool 自签名
