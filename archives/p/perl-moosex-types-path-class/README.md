# perl-moosex-types-path-class

MooseX::Types::Path::Class — 为 MooseX::Types 提供 Path::Class 类型的路径类型约束。

## 简介

该模块为 MooseX::Types 类型库系统添加了以下路径类型约束：

- **Dir** — 对应 `Path::Class::Dir`，支持从字符串自动强制转换
- **File** — 对应 `Path::Class::File`，支持从字符串自动强制转换

这些类型约束可以用于 Moose 属性定义中，实现对路径参数的类型安全和自动转换。

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.09 | published | 2026-06-24 |

## 鸿蒙平台兼容性

- ✅ 纯 Perl 模块，无 XS 组件
- ✅ 无需 ELF 签名
- ✅ 无 SELinux HMDFS 限制
- ✅ 无需 HNP 安装步骤
- ✅ 通过 cmd-pkgs 公共安装脚本部署后直接可用

## 运行时依赖

- Perl ≥ 5.006
- Moose
- MooseX::Types
- Path::Class ≥ 0.16

## 许可证

Perl 5 (GPL/Artistic)
