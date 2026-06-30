# FreeImage

## 软件简介
FreeImage 是一个开源库项目，面向需要支持 PNG、BMP、JPEG、TIFF、WebP、HEIF 等现代多媒体应用中常用图形图像格式的开发者。

## 版本: 3.18.0

### 支持的图像格式
- BMP, CUT, DDS, EXR, GIF, HDR, ICO, IFF, JBIG, JNG, JP2, JPEG, JPEG XR (JXR), KOALA, MNG, PCD, PCX, PFM, PICT, PNG, PNM, PSD, RAS, RAW, SGI, TARGA, TIFF, WBMP, WebP, XBM, XPM

### 主要特性
- 自包含库，内嵌编解码器（libPNG、libJPEG、libTIFF、zlib、OpenJPEG、OpenEXR、LibRaw、LibWebP、LibJXR）
- 同时输出静态库（.a）和动态库（.so）
- C 语言 API，跨平台

## 鸿蒙平台编译配置
- **构建系统**: 自定义 Makefile（Makefile.gnu）
- **编译器**: clang/clang++ 15.0
- **架构**: aarch64
- **关键编译参数**: -fPIC -O2 -fexceptions -fvisibility=hidden -DPNG_ARM_NEON_OPT=0
- **安装前缀**: /usr/local（可通过 PREFIX 变量配置）

## 依赖说明
FreeImage 内嵌所有依赖，无需外部库：
- libJPEG, libPNG, libTIFF4, ZLib, LibOpenJPEG, OpenEXR, LibRawLite, LibWebP, LibJXR

## 鸿蒙平台功能测试结果
- **测试状态**: ✅ 通过（20/20 项测试全部通过）
- **测试日期**: 2026-06-24
- **测试覆盖**: 库初始化、图像创建、像素操作、BMP/PNG/JPEG/TIFF 读写、色彩转换、缩放旋转、伽马校正、调色板操作
- **动态库**: ✅ 编译链接运行均正常
- **静态库**: ⚠️ 上游 main 符号冲突，需加 `-Wl,--allow-multiple-definition`
- **结论**: FreeImage 3.18.0 在鸿蒙平台功能完全正常，可用于生产环境
