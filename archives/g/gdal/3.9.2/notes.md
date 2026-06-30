# gdal 3.9.2 适配笔记

## 编译环境
- 构建系统: cmake (CMake 4.1.2)
- 编译日期: 2026-05-28
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built ✅

## 编译步骤

### 依赖编译（前置工作）

首先编译了 GDAL 的核心依赖链：

1. **OpenSSL 3.5.6** ✅ 已存在（系统预编译）
2. **SQLite3 3.46.0** ✅ 已编译（手动编译 amalgamation 版本）
3. **TIFF 4.6.0** ✅ 已存在
4. **PROJ 9.8.1** ✅ 已编译（需要 SQLite3 + OpenSSL）

### GDAL 编译

```bash
export SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export CMAKE_PREFIX_PATH="$HOME/usr/local:$CMAKE_PREFIX_PATH"
python3 $SKILL_ROOT/scripts/ohc-run.py build gdal --resume-from=Step3
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GDAL CMake 配置失败：缺少 PROJ | PROJ 是 GDAL 的核心依赖 | 先编译 PROJ 9.8.1 |
| 2 | PROJ 编译失败：缺少 SQLite3 | SQLite3 未安装 | 手动编译 SQLite3 3.46.0 |
| 3 | WebP 链接错误：SharpYuvInit undefined | libsharpyuv 未正确链接 | 禁用 WebP：`-DGDAL_USE_WEBP=OFF` |
| 4 | Arrow 相关警告 | Arrow 配置不完整 | 禁用 Arrow/Parquet：`-DArrow_FOUND=OFF` |

## 最终 CMake 配置选项

```bash
-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local
-DArrow_FOUND=OFF
-DParquet_FOUND=OFF
-DArrowDataset_FOUND=OFF
-DGDAL_USE_WEBP=OFF
```

## 源码修改

无源码修改。

## 依赖版本

**已成功编译/存在的依赖**：
- OpenSSL 3.5.6 ✅
- SQLite3 3.46.0 ✅
- TIFF 4.6.0 ✅
- PROJ 9.8.1 ✅
- zlib 1.3.1 ✅
- curl 8.8.0 ✅
- libxml2 2.12.10 ✅
- ZSTD 1.5.6 ✅
- PNG 1.6.43 ✅
- JPEG 62 ✅
- JXL (libjxl) ✅
- PCRE2 ✅
- libiconv ✅

**禁用的依赖**：
- WebP（因 libsharpyuv 链接问题）
- Arrow/Parquet（配置不完整）

## 验证结果

```bash
# pkg-config 验证
$ export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
$ pkg-config --modversion gdal
3.9.2

$ pkg-config --cflags gdal
-I/storage/Users/currentUser/usr/local/include

$ pkg-config --libs gdal
-L/storage/Users/currentUser/usr/local/lib -lgdal

# gdal-config 验证
$ ~/usr/local/bin/gdal-config --version
3.9.2

# 库文件
$ ls -la ~/usr/local/lib/libgdal.so
-rwxrwx--- 1 file_manager 25799296 2026-05-28 21:31 libgdal.so (24.5MB)

# 工具
$ ls ~/usr/local/bin/gdal*
gdal-config  gdal_contour  gdal_create  gdal_footprint  gdal_grid
gdal_rasterize  gdal_translate  gdal_viewshed  gdaladdo  gdalbuildvrt
gdaldem  gdalenhance  gdalinfo  gdallocationinfo  gdalmanage
gdalmdiminfo  gdalmdimtranslate  gdalsrsinfo  gdaltindex  gdaltransform
gdalwarp  ogr2ogr  ogrinfo  ogrlineref  ogrtindex
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ~/usr/local/lib/libgdal.so | 24.5MB | GDAL 共享库 |
| ~/usr/local/lib/pkgconfig/gdal.pc | - | pkg-config 文件 |
| ~/usr/local/include/gdal*.h | ~ | 头文件集 |
| ~/usr/local/bin/gdal-config | - | 配置脚本 |
| ~/usr/local/bin/gdal_* | ~ | GDAL 工具集 (20+) |
| ~/usr/local/bin/ogr_* | ~ | OGR 工具集 |

## 运行时注意事项

1. **动态链接路径**：GDAL 可执行文件使用相对路径 `../libgdal.so`，在 HarmonyOS 环境下需要：
   - 确保 libgdal.so 在正确位置
   - 设置 LD_LIBRARY_PATH 或在部署时调整 RPATH

2. **依赖库路径**：运行时可能需要设置：
   ```bash
   export LD_LIBRARY_PATH="$HOME/usr/local/lib:$LD_LIBRARY_PATH"
   ```

3. **测试执行**：GDAL CMake 项目不提供 `make check` 目标，测试需使用 `ctest` 或其他方式。

---
**编译结束**: 2026-05-28 21:37
**最终状态**: built ✅
**总耗时**: 约 2 小时（包含依赖编译）