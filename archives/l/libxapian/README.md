# libxapian

## 简介

libxapian 是 Xapian 开源全文检索引擎的核心库（上游源码包名为 xapian-core，
库文件为 `libxapian.so`），提供概率信息检索 API、glass/honey/inmemory/remote
多后端数据库、查询解析与词干提取能力。

## 基本信息

- **软件名称**: libxapian
- **显示名**: Xapian Search Engine Library
- **描述**: 开源全文检索引擎库
- **分类**: library
- **官网**: https://xapian.org/
- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools
- **上游源码**: https://oligarchy.co.uk/xapian/2.0.0/xapian-core-2.0.0.tar.xz

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.0.0 | built | 2026-09-18 |

## OHOS 适配说明

本软件已适配 OHOS 系统，使用 autotools 构建系统。
与 `archives/x/xapian-core/2.0.0` 同源（同一上游 tarball、同一组可移植补丁），
配方逻辑保持一致，包名取库名 `libxapian`。

## 相关链接

- [官方网站](https://xapian.org/)
- [2.0.0 编译文档](./2.0.0/notes.md)

## 编译说明

请查看具体版本的 `manifest.yaml` 和 `notes.md` 文件了解详细的编译配置和注意事项。
