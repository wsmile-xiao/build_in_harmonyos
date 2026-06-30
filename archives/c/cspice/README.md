# cspice — NAIF SPICE Toolkit for C

## 软件描述

cspice 是 NASA/JPL NAIF (Navigation and Ancillary Information Facility) 开发的 SPICE 工具包的 C 语言版本。SPICE 是一个观测几何系统，用于机器人空间科学任务的数据处理和分析。

SPICE 系统提供：
- 行星历表和航天器位置计算
- 时间转换和历元处理
- 参考系变换
- 几何观测计算（光照、遮挡、视场等）
- 科学数据文件读写（SPK、CK、PCK、EK、DSK、DAS、DAF 等格式）

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 67 | built | 2026-06-29 |

## 构建系统

cspice 使用自定义 Makefile（非 autotools/cmake）。源码包含约 2151 个 C 源文件，编译为单个静态库 `libcspice.a`。

## 许可证

NAIF 自定义许可证（非标准开源许可证）。使用前需查阅 NAIF 的许可条款。

## 主页

- NAIF Toolkit: https://naif.jpl.nasa.gov/naif/toolkit_C.html
- GitHub 镜像: https://github.com/arturania/cspice

## 依赖

无外部依赖。cspice 是自包含的 C 库。

## 已归档版本

- [67](67/) — 2026-06-29 编译，状态: built
