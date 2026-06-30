# tmx — Tiled Map Editor XML 解析库

## 简介

tmx 是一个 C 语言编写的 Tiled Map Editor (.tmx) XML 地图文件解析库。它可以将 Tiled 地图编辑器生成的 .tmx 文件解析为 C 数据结构（`tmx_map`），供游戏引擎或地图渲染程序使用。

## 功能特性

- 解析 .tmx XML 地图文件（含图层、瓦片集、对象组、属性等）
- 支持 orthogonal、isometric、staggered、hexagonal 地图方向
- 支持 CSV、Base64（raw/zlib/zstd）数据编码
- 支持从文件、缓冲区、文件描述符、回调函数加载
- 资源管理器（`tmx_resource_manager`）预加载外部瓦片集和模板
- 自定义内存分配器和图像加载回调
- BSD-2-Clause 许可证

## 版本信息

| 项目 | 值 |
|------|---|
| 名称 | tmx |
| 版本 | 1.10.1 |
| 许可证 | BSD-2-Clause |
| 语言 | C |
| 构建系统 | cmake |
| 依赖 | zlib, libxml2 |

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.10.1 | published | 2026-06-16 |

## 源码

- 仓库: https://github.com/baylej/tmx
- 发布包: https://github.com/baylej/tmx/archive/refs/tags/tmx_1.10.1.tar.gz

## 预编译包

- `tmx-1.10.1-ohos-aarch64.tar.gz` (122KB)
  - 包含: `include/tmx.h`, `lib/libtmx.a`, cmake 配置文件
