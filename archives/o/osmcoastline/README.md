# osmcoastline

> OSMCoastline — 从 OpenStreetMap 数据提取海岸线并转换为 GIS 格式的命令行工具。

## 简介

OSMCoastline 读取 OpenStreetMap 的海岸线数据，将其提取、简化并输出为
Shapefile、GeoPackage 或 Spatialite 数据库。它基于 libosmium 库处理 OSM 数据，
使用 GDAL/OGR 进行矢量数据输出，GEOS 进行几何操作。

## OHOS 适配要点

- CMake + `ohos.toolchain.cmake`；`package_type="application"`（无 shared 选项）
- **libosmium 和 protozero 无 Conan 制品**：在 `build()` 中下载 header-only 源码
  并通过 CMake 缓存变量 `OSMIUM_INCLUDE_DIR` / `PROTOZERO_INCLUDE_DIR` 注入
- C++ 标准同步 profile `cppstd=17`（上游默认 14）
- LZ4 支持开启（`lz4/1.10.0` 在 ohpcd 可用）
- 上游 CTest 42 用例需要 spatialite 运行时（设备端缺失）

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | ohpcd |
| expat | 2.8.2.1 | ohpcd |
| bzip2 | 1.0.8 | ohpcd |
| gdal | 3.9.2.1 | ohpcd |
| geos | 3.13.0 | ohpcd |
| lz4 | 1.10.0 | ohpcd |
| libosmium | 2.20.0 | vendored (header-only) |
| protozero | 1.7.1 | vendored (header-only) |

## 参考

- [官网](https://osmcode.org/osmcoastline/)
- [源码仓库](https://github.com/osmcode/osmcoastline)
