# barvinok

barvinok 是用于计算参数化或非参数化多面体整数点数量的 GPL-2.0 库，
同时提供 `iscc`、`barvinok_enumerate`、`barvinok_count` 等命令行工具。

## 版本

- 0.41.9

## 适配范围

- 构建系统：Autotools
- 目标平台：Linux、OpenHarmony PC
- 默认静态构建 barvinok、PolyLib 和 isl
- 使用 Conan 的 `gmp/6.3.0.1` 与 `ntl/11.6.0.2`
- PolyLib 和 isl 使用上游源码包内版本
- 未启用可选的 PET、GLPK、cddlib 和 TOPCOM 集成

## 交付内容

- 头文件：barvinok、isl、PolyLib
- 静态库：`libbarvinok.a`、`libpolylibgmp.a`、`libisl.a`
- 工具：`iscc`、`barvinok_count`、`barvinok_enumerate`、`barvinok_enumerate_e`、
  `barvinok_ehrhart` 及 PolyLib 辅助工具

官方源码发布在 [barvinok SourceForge](https://sourceforge.net/projects/barvinok/files/)，
本归档使用 0.41.9 的 `tar.bz2` 源码包。
