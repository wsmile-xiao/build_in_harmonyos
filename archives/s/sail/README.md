# SAIL

SAIL（Squirrel Abstract Imaging Library）是一个快速、轻量的 C11 图像解码/编码库，
提供从一行式 API（junior）到深度定制（technical diver）的完整接口。支持 20+ 种图像
格式（PNG、JPEG、GIF、TIFF、BMP、QOI、ICO 等）、多页与动画、元数据与 ICC 配置。

- 上游仓库：https://github.com/HappySeaFox/sail
- 官网：https://sail.software
- 许可：MIT

## 功能概述

- 可插拔 codec 架构，codec 可组合进单一库（static 自动 `SAIL_COMBINE_CODECS=ON`）
- 高层 API：`sail_load_from_file()` / `sail_load_from_memory()` 一行解码
- 线程安全（`SAIL_THREAD_SAFE`）
- 多源 I/O：文件、内存、自定义流
- 元数据 / EXIF / ICC 支持

## OHOS 适配

- 原生 CMake 构建（OHOS aarch64），非交叉编译。
- 启用 codec：PNG、JPEG、GIF、TIFF（Conan 依赖）+ BMP、PCX、PNM、PSD、TGA、WAL、
  XBM、XPM、XWD、HDR、ICO、QOI（自包含）。
- C++ binding（sail-c++）按上游默认开启（`SAIL_BUILD_BINDINGS=ON`），其 tests/bindings/c++
  16 个用例一并注册，上游测试总数完整为 N=48。
- 未启用 codec：webp（config 目标缺失）、avif/heif/jpeg2000/jpegxl/openexr/jbig
  （依赖过大）、svg（缺 nanosvg）。测试套件随之只覆盖启用 codec 的格式。
- codec 依赖通过模块 find_package（FindPNG/JPEG/GIF/TIFF）经 `CMAKE_PREFIX_PATH`
  （Conan CMakeDeps 注入）解析。

## 依赖关系

- 编译/运行依赖：giflib、libpng、libjpeg、libtiff。

## 参考资料

- 上游源码：https://github.com/HappySeaFox/sail
- ConanCenter 配方参考：https://github.com/conan-io/conan-center-index/tree/master/recipes/sail
