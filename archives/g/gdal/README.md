# GDAL

> Geospatial Data Abstraction Library — 栅格与矢量地理空间数据抽象库。

## 简介

GDAL 提供统一的读写与转换接口，覆盖常见栅格/矢量格式，并与 PROJ 坐标转换联动。
本仓库交付 OHOS aarch64 上的 Conan 配方（最小驱动集，供 simple-tiles 等消费）。

## OHOS 适配要点

- CMake + `ohos.toolchain.cmake`；原生 OHOS aarch64 构建
- 必需依赖：`proj` / `sqlite3` / `zlib`；TIFF/GeoTIFF 用源码树内置
- 默认关闭 GEOS / CURL / WebP / Arrow 等可选依赖（可按 ohpcd 配方进展打开）
- OHOS `/tmp` 只读：勿假设 POSIX 可写 `/tmp`；上游相关探测用例已按规范豁免
- 发行 tarball 不含 `autotest/`；完整 C++ 套件需 `gdalautotest`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| proj | 9.3.1.1 | 坐标转换 |
| sqlite3 | 3.49.1 | GPKG / SQLite |
| zlib | 1.3.1.1 | 压缩 |

## 功能验证

```bash
conan create archives/g/gdal/3.9.2.1 \
  --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing
# test_package 期望: gdal ok version=3.9.2 drivers=<N>
gdal-config --version   # → 3.9.2
```

上游 C++ 单元测试（W4）：652/674（96.7%）；扣除豁免与 skip 后 652/652（100%）。
详见 [3.9.2.1/test_package/MANIFEST.yml](./3.9.2.1/test_package/MANIFEST.yml)。

## 参考

- [官方文档](https://gdal.org/)
- [源码仓库](https://github.com/OSGeo/gdal)
- 测试与豁免声明: [3.9.2.1/test_package/MANIFEST.yml](./3.9.2.1/test_package/MANIFEST.yml)
