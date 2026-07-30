# libtiff

## 简介
TIFF image format library

## OHOS 适配
- 构建系统: CMake
- 版本: 4.6.0
- 依赖: zlib/1.3.1, libjpeg/10
- 构建选项: 静态库 (BUILD_SHARED_LIBS=OFF)
- 可选依赖已禁用: JBIG, LERC, LZMA, ZSTD, WebP, libdeflate

## 关键适配点
1. CMake 4.x 兼容: 需要 CMAKE_POLICY_VERSION_MINIMUM=3.5 (doc/CMakeLists.txt 使用旧版本要求)
2. 平台识别: CMAKE_SYSTEM_NAME=Linux (CMake 不识别 OHOS, E092)
3. 源码目录有 build/ 子目录, 不能在源码内构建 (需 out-of-source)
4. 产物: libtiff.a, libtiffxx.a, 工具 (tiffinfo, tiffcp, tiffdump, tiffset, tiffsplit)

## 功能验证
- tiffinfo --version 输出正确版本号
- test_package 创建/读取 TIFF 文件成功

## 参考
- https://libtiff.gitlab.io/libtiff/
