# libics

## 简介
ICS（Image Cytometry Standard）参考读写库，支持任意维度与数据类型的显微图像及采集元数据存取。

## OHOS 适配
- 上游同时提供 CMake 与 Autotools 构建，本配方选用 CMake（conan 依赖注入更直接）
- zlib 依赖由 Conan 提供，通过 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY 显式注入，不依赖系统 zlib
- 产物库名为 libics.a，对应 cpp_info.libs 为 ics（上游 OUTPUT_NAME 所致）
- 上游 ctest 套件在配方 build() 内完整执行并输出机器证据标记

## 依赖
- zlib/1.3.1

## 功能验证
- 上游 ctest：test_ics1/test_ics2a/test_ics2b/test_gzip/test_compress/test_strides（1-3）/test_metadata（1-4）/test_history
- test_package：创建 ICS 文件并验证布局、数据往返与历史记录（5 项检查）

## 参考
- 上游仓库: https://github.com/svi-opensource/libics
- 文档: https://svi-opensource.github.io/libics
