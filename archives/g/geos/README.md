# GEOS (Geometry Engine Open Source)

## 简介
GEOS 是一个 C++ 几何库，是 JTS (Java Topology Suite) 的 C++ 移植版本。
用于地理空间数据处理，支持各种几何操作。

## 官方网站
https://libgeos.org/

## 源码下载
https://download.osgeo.org/geos/

## 已编译版本
- 3.13.0 (静态库版本)
- 3.13.1 (conan 动态库，libgeos.so + libgeos_c.so，真机验证)
- 3.14.1 (conan 动态库，libgeos.so + libgeos_c.so + geosop，真机验证)

## 依赖关系
无外部依赖

## 注意事项
- 建议编译为静态库（BUILD_SHARED_LIBS=OFF）
- 动态库版本存在 RPATH 相对路径问题
