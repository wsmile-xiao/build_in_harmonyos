# postgis 3.4.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 准备依赖
确保以下依赖已安装：
- PostgreSQL 17.2（包括 pg_config）
- GEOS 3.13.0
- PROJ 9.8.1
- libiconv 1.17

### 2. 创建 libiconv.so 软链接
```bash
cd ~/usr/local/lib
rm -f libiconv.so
ln -s libiconv.so.2.6.1 libiconv.so
```

### 3. 运行 configure
```bash
./configure --prefix=$DEFAULT_PREFIX \
  --with-pgconfig=$DEFAULT_PREFIX/bin/pg_config \
  --with-geosconfig=$DEFAULT_PREFIX/bin/geos-config \
  --with-libiconv-prefix=$DEFAULT_PREFIX \
  --without-protobuf \
  --without-raster \
  --without-topology \
  --without-json
```

### 4. 编译
```bash
make -j2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GEOS链接失败 | libgeos_c.a静态库缺少libgeos.a和C++ stdlib | 修改configure.ac添加`GEOS_LDFLAGS="$GEOS_LDFLAGS -lgeos -lc++"` |
| 2 | libiconv链接失败 | configure检测错误，使用了-lc而非-liconv | 使用`--with-libiconv-prefix`参数强制链接libiconv |
| 3 | libiconv.so不存在 | 预编译包缺少软链接 | 创建libiconv.so软链接指向libiconv.so.2.6.1 |

## 依赖版本
- postgresql: 17.2
- geos: 3.13.0
- proj: 9.8.1
- libxml2: 2.11.9
- libiconv: 1.17

## 验证结果
```bash
# 检查编译产物
ls -la loader/shp2pgsql loader/pgsql2shp postgis/postgis-3.so
```

成功生成的产物：
- loader/shp2pgsql (4.3MB)
- loader/pgsql2shp (4.3MB)
- postgis/postgis-3.so (7.3MB)

## 交付物
核心编译产物已生成，status=built。

---
**编译结束**: 2026-05-28
**最终状态**: built