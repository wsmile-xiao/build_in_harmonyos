# Xapian

## 简介

Xapian 是全文检索引擎库。本归档提供 Conan 包 `xapian`，上游源码发布名仍为 `xapian-core`。

## 基本信息

- **软件名称**: xapian
- **显示名**: Xapian
- **官网**: https://xapian.org/
- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools
- **包含工具**: `xapian-check`、`xapian-delve`、`xapian-compact`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.0 | built | HarmonyOS PC aarch64，依赖 zlib/1.3.1.1 |

## 适配说明

详细构建选项、移植补丁与验证边界见 [2.0.0/notes.md](./2.0.0/notes.md)。
本归档与 `xapian-core/2.0.0` 使用相同上游源码和已归档移植补丁，但 Conan 包身份及测试声明独立为 `xapian/2.0.0`。
