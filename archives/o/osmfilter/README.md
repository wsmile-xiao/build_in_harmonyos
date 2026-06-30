# osmfilter

OpenStreetMap 数据过滤工具，属于 osmctools 工具套件。

## 简介

osmfilter 是一个命令行工具，用于过滤 OpenStreetMap 数据。它可以根据标签、地理区域或其他条件从 OSM 文件中选择特定元素（节点、路径、关系）。

osmctools 套件还包含：
- **osmconvert**：在不同 OSM 文件格式之间转换（依赖 zlib）
- **osmupdate**：下载和更新 OSM 数据文件

## 许可证

AGPL-3.0

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.9 | 已编译 | 2026-06-16 |

## 构建系统

autotools（从 git 源码构建时需先运行 `autoreconf -fi`）

## 已知注意事项

- HMDFS 上 config.status 的 umask 需从 077 改为 007（E081）
- 源码为 git 仓库，init-build 不直接支持，需手动 clone 并打包为 tar.gz
