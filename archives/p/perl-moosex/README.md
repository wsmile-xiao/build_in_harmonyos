# perl-moosex

MooseX 命名空间文档模块。该模块定义并文档化了 CPAN 上 MooseX::* 命名空间的使用规范，是 Moose 扩展生态系统的核心基础模块。

## 基本信息

- **上游**: https://metacpan.org/dist/MooseX
- **许可证**: Perl Artistic License (同 Perl 本身)
- **作者**: Karen Etheridge <ether@cpan.org>
- **当前版本**: 0.002

## 功能说明

MooseX 0.002 是一个纯 Perl 模块，仅包含 POD 文档，用于：
- 文档化 MooseX::* 命名空间的使用规范
- 为 Moose 扩展开发者提供命名约定指导
- 作为 MooseX 生态系统的命名空间锚点

## 平台支持

- **OpenHarmony aarch64**: ✅ 已验证可用
- **纯 Perl 模块**: 无 C/XS 代码，无平台兼容性问题
- **HMDFS 安全**: 纯 Perl 模块在 HMDFS 上无 SELinux 限制

## 安装依赖

### MooseX 0.002 核心
- Perl >= 5.006
- strict, warnings (核心模块)

### MooseX 生态系统（按需安装）
- MooseX::Types 0.51 及其依赖:
  - Carp::Clan >= 6.00
  - Sub::Exporter::ForMethods >= 0.100052
- Moose 及其依赖:
  - Context::Preserve

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 0.002 | 2026-06-24 | published | 编译成功，功能验证通过 |
