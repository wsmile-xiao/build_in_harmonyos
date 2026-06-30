# perl-moosex-types-datetime

MooseX::Types::DateTime — 为 MooseX::Types 提供 DateTime 相关的类型约束和强制转换。

## 简介

该模块为 MooseX::Types 类型库系统添加了以下日期时间类型约束：

- **DateTime** — 对应 `DateTime` 对象，支持从 epoch 时间戳、Hash 参数和字符串自动强制转换
- **Duration** — 对应 `DateTime::Duration` 对象，支持从 Hash 参数自动强制转换
- **DateTime::Locale** — 对应 `DateTime::Locale` 对象，支持从 locale 字符串（如 `"en"`、`"zh_CN"`）自动强制转换
- **DateTime::TimeZone** — 对应 `DateTime::TimeZone` 对象，支持从时区字符串（如 `"UTC"`、`"Asia/Shanghai"`）自动强制转换

这些类型约束可用于 Moose 属性定义中，实现对日期时间参数的类型安全和自动转换。

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.13 | built | 2026-06-24 |

## 鸿蒙平台兼容性

- ✅ 纯 Perl 模块，无 XS 组件
- ✅ 无需 ELF 签名
- ✅ 无 SELinux HMDFS 限制
- ✅ 无需 HNP 安装步骤
- ✅ 通过 cmd-pkgs 公共安装脚本部署后直接可用
- ⚠️ 依赖 DateTime（运行于纯 Perl 模式，XS 因 musl 头文件不完整无法编译，但功能完整）

## 运行时依赖

- Perl ≥ 5.008003
- Moose ≥ 0.41
- MooseX::Types ≥ 0.30
- MooseX::Types::Moose ≥ 0.30
- DateTime ≥ 0.4302（当前 1.66，纯 Perl 模式）
- DateTime::Duration ≥ 0.4302（随 DateTime 安装）
- DateTime::Locale ≥ 0.4001（当前 1.45）
- DateTime::TimeZone ≥ 0.95（当前 2.68）
- namespace::clean ≥ 0.19

## 测试结果

- make test: ✅ 全部通过（4 文件，27 测试）
- 模块加载: ✅ 通过
- Moose 类集成: ✅ 通过
- 类型约束导出: ✅ 通过
- 功能扩展测试: ✅ 10/10 通过

## 许可证

Perl 5 (GPL/Artistic)
