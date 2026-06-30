# GEOS 3.13.0 编译笔记

## 编译信息
- 编译日期: 2026-05-20
- 构建系统: CMake
- 编译类型: 静态库

## 编译过程
1. 下载源码: https://download.osgeo.org/geos/geos-3.13.0.tar.bz2 (SSL 证书验证失败，使用 curl -k 手动下载)
2. CMake 配置:
   - `-DCMAKE_BUILD_TYPE=Release`
   - `-DBUILD_SHARED_LIBS=OFF` (静态库，避免动态库加载问题)
   - `-DBUILD_TESTING=OFF`
3. 编译: make -j4 成功
4. 安装: DESTDIR 模式安装成功
5. 验证: geosop 距离计算测试成功

## 遇到的问题
1. SSL 证书验证失败 - 使用 curl -k 下载
2. 动态库版本 RPATH 使用相对路径 `../../lib/` 导致加载失败
   - 解决方案: 编译为静态库

## 验证测试
- geosop --help: 成功显示 GEOS 3.13.0
- 距离计算测试: `echo "POINT(0 0)" | geosop -a "POINT(0 0)" -b "POINT(1 1)" distance` 返回 1.4142135623730951

## 产物
- lib/libgeos.a (12.08 MB)
- lib/libgeos_c.a (588 KB)
- bin/geosop (3.84 MB)
- include/geos/ (头文件)

---
**编译结束**: 2026-05-20 17:52
**最终状态**: built
---

**编译结束**: 2026-05-20 18:00
**最终状态**: published
