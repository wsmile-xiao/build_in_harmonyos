# libgeotiff

## 简介
Library for reading and writing GeoTIFF tags in TIFF files. GeoTIFF 代表地理参照的 TIFF 文件格式，包含坐标参照系统和地理变换信息。

## OHOS 适配
- 构建系统: CMake
- 目标平台: OpenHarmony aarch64 (OHOS 6.0, clang 15, libc++, cppstd17)
- 详见各版本 notes.md 获取适配详情

## 依赖
- libtiff (TIFF I/O)
- proj (坐标转换)
- zlib (压缩，通过 libtiff 传递)
- libjpeg-turbo (JPEG 压缩，通过 libtiff 传递)

## 功能验证
- conan create 编译验证通过
- test_package ctest 1/1 通过
- 功能测试: 创建/读取 GeoTIFF 文件，GTIFNew/GTIFKeySet/GTIFWriteKeys/GTIFKeyGet API 验证通过
- 详见各版本 notes.md

## 参考
- https://github.com/OSGeo/libgeotiff
- https://geotiff.readthedocs.io/
