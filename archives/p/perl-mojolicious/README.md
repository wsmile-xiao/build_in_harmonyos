# perl-mojolicious

Perl 实时 Web 框架，提供完整的 MVC 架构、路由、模板、WebSocket、HTTP 客户端等功能。

## 软件信息

- **版本**: 9.42 (Waffle)
- **主页**: https://mojolicious.org
- **CPAN**: https://metacpan.org/dist/Mojolicious
- **许可**: Artistic License 2.0
- **构建系统**: Perl Makefile.PL (ExtUtils::MakeMaker)

## 依赖

- Perl >= 5.016
- IO::Socket::IP >= 0.37 (系统预装)
- Sub::Util >= 1.41 (系统预装)

## 鸿蒙平台适配

### 已知限制

1. **prctl(PR_SET_NAME) 不完全支持**: OpenHarmony 内核的 `prctl(PR_SET_NAME)` 返回 `EINVAL`，导致 Perl `$0` 赋值失败。已通过 3 个补丁修复，用 `eval` 包裹 `$0` 赋值。

2. **Mojo::Pg 数据库适配器**: 依赖 DBD::Pg XS 模块，受 SELinux HMDFS 限制无法从用户目录加载。需将 DBD::Pg 安装到系统目录。

### 补丁列表

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-lib-Mojo-Server.pm.patch | lib/Mojo/Server.pm | load_app() $0 赋值 eval 包裹 |
| 0002-lib-Mojo-Server-Hypnotoad.pm.patch | lib/Mojo/Server/Hypnotoad.pm | run() $0 赋值 eval 包裹 |
| 0003-lib-Mojo-Server-Morbo.pm.patch | lib/Mojo/Server/Morbo.pm | run() $0 赋值 eval 包裹 |

## 版本记录

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 9.42 | built | 2026-06-23 | 修复 prctl 平台限制，109/109 测试通过 |
