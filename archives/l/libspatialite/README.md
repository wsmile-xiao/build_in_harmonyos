# SpatiaLite

> SQLite spatial database extension with OGC geometry support

## 简介

SpatiaLite 是 SQLite 数据库的空间扩展，支持 OGC（Open Geospatial Consortium）几何对象标准。它提供完整的 SQL 空间函数库，包括：

- 几何对象创建与转换
- 空间关系判断（相交、包含、距离等）
- 空间分析函数（缓冲区、几何运算等）
- WKT/WKB 格式支持
- GeoJSON 导入导出

适用于轻量级 GIS 应用、嵌入式空间数据存储、移动端地图应用等场景。

## OHOS 适配要点

1. **HMDFS 权限问题（E011）**：configure 使用 `umask 077` 创建临时目录会导致权限错误，需修改为 `umask 022`
2. **平台识别**：config.guess/config.sub 需支持 `aarch64-unknown-linux-ohos`
3. **可选依赖**：PROJ/FreeXL/GEOS/minizip 无预编译包，编译时禁用
4. **条件编译**：禁用 GEOS 时需添加 `#ifdef HAVE_GEOS_C_H` 守卫（demo2.c）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| sqlite3 | 3.49.1 | 核心依赖（预编译包） |
| libxml2 | 2.13.5 | XML 支持（预编译包） |
| zlib | 1.3.1 | 压缩支持（预编译包） |

## 功能验证

```bash
# 检查库版本
pkg-config --modversion spatialite

# 测试空间函数
sqlite3 :memory: "SELECT Spatialite_Version();"

# 加载空间扩展
sqlite3 test.db "SELECT load_extension('mod_spatialite');"
```

## 参考

- [官方文档](https://www.gaia-gis.it/fossil/libspatialite/wiki?name=Documentation)
- [源码仓库](https://www.gaia-gis.it/fossil/libspatialite)