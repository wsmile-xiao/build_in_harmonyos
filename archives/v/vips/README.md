# VIPS (Visual Image Processing System)

## 简介
VIPS 是一个高性能的图像处理库，专为处理大型图像而设计。它支持广泛的图像格式和操作，包括：
- 图像加载和保存
- 基本图像操作（裁剪、缩放、旋转）
- 颜色转换和调整
- 滤镜和特效
- 图像分析

## 特点
- **高性能**：采用惰性计算和流水线处理，适合处理大型图像
- **低内存占用**：流式处理，不需要一次性加载整个图像
- **多格式支持**：支持 JPEG、PNG、TIFF、WebP、HEIF、OpenEXR 等多种格式
- **丰富的 API**：提供 C、C++、Python、Ruby 等多种语言接口

## 鸿蒙适配要点

### 构建系统
- 使用 meson 构建系统
- 需要设置 `PKG_CONFIG_PATH` 环境变量指向预编译包的 pkg-config 目录

### 关键依赖
- glib-2.0 (核心依赖)
- libtiff-4 (需要传递依赖 liblzma)
- libjpeg-turbo
- zlib
- xz/lzma
- lcms2
- OpenEXR
- libopenjp2 (OpenJPEG)
- libheif

### 平台特定修改
1. **传递依赖检测**：meson 对静态库的传递依赖检测不完整，需要手动添加传递依赖到功能检测中
2. **toybox rm 兼容性**：ninja 的 STATIC_LINKER 规则使用 `rm -f` 前置命令，需要修改 build.ninja 或使用 GNU rm wrapper
3. **软链接创建**：HMDFS 不支持 `ln -sf` 覆盖，需要使用 `rm -f && ln -s`

### 编译命令
```bash
# 设置环境变量
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export CC=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang
export CXX=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++

# 配置和编译
cd ~/tmp/builds/vips-8.18.2.work
meson setup builddir --prefix=/storage/Users/currentUser/usr/local \
    -Dfontconfig=disabled \
    -Dpangocairo=disabled \
    -Dpng=disabled \
    -Dspng=disabled
ninja -j4

# 安装（DESTDIR 模式）
ninja install
```

## 使用示例
```bash
# 查看版本
vips --version

# 图像转换
vips jpgsave input.png output.jpg --quality=90

# 图像缩放
vipsthumbnail input.jpg -o output.jpg -s 300

# 查看图像信息
vipsheader input.tiff
```

## 版本历史
- 8.18.2: built (2026-05-29)
- 8.15.4: built (2026-05-27)
- 8.15.2: built (2026-05-27)

## 参考资料
- 官方文档：https://libvips.github.io/libvips/
- GitHub：https://github.com/libvips/libvips