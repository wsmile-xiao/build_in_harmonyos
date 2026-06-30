# perl-sentinel

**Sentinel** — Create lightweight SCALARs with get/set callbacks (Perl XS module)

## 简介

Sentinel 提供 `sentinel` lvalue 函数，用于创建带有 get/set 回调的轻量级标量。主要用于创建 lvalue 对象访问器，使赋值操作能触发实际代码执行，而非简单更新标量变量。

## 版本

- **当前版本**: 0.07-r2
- **CPAN**: https://metacpan.org/dist/Sentinel
- **作者**: Paul Evans (PEVANS)

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | Perl XS (ExtUtils::MakeMaker) |
| 编译器 | clang 15 |
| 平台 | OpenHarmony 6.0 (aarch64) |
| Perl | 5.42.0 |
| 状态 | built |

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.07-r2 | built | 2026-06-29 |

## 依赖

- Perl 5.42.0 (系统预装)
- clang (系统工具链)
- ExtUtils::MakeMaker (Perl 内置)

## 安装

```bash
# Conan 安装
conan install --requires=perl-sentinel/0.07-r2@ohpcd/stable
```

## 注意事项

- .so 在 OHOS HMDFS/tmpfs 上无法 dlopen (SELinux `hmmac=use_task` 限制)
- Sentinel.pm 自动回退到 Pure Perl 实现 (Sentinel::PP, tied scalar)
- PP 模式: get 回调正常工作, set 回调因 tied scalar magic 在 sv_setsv 时丢失不工作
- XS 模式 (需 .so 可加载): get/set 回调均正常 (使用 PERL_MAGIC_ext + CvLVALUE_on)
- 参考 perl-dbd-pg 编译经验: XS 模块在 OHOS 上 .so 有加载限制
- ELF 已包含 .note.ohos.ident 和 .codesign 签名段
