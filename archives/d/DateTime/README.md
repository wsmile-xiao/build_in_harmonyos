# DateTime

Perl DateTime 模块 - 日期时间对象处理库。

## 简介

DateTime 是 Perl 的核心日期时间处理模块，提供完整的日期时间对象实现，包括：
- 日期时间创建和解析
- 时区支持
- 日期运算和比较
- 格式化和国际化

## 技术细节

- **构建系统**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **语言**: Perl + XS（C 扩展）
- **依赖**: DateTime::Locale, DateTime::TimeZone, musl

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.66 | built | 2026-06-10 | XS 编译成功，SELinux 限制阻塞运行 |

## 注意事项

⚠️ **SELinux HMDFS 限制**: 用户目录上的动态库无法加载，需管理员安装到 `/data/service/hnp` 系统目录。

## 参考链接

- CPAN: https://metacpan.org/pod/DateTime
- 源码: https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/DateTime-1.66.tar.gz