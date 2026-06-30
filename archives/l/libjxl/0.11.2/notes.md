# libjxl 0.11.2 编译笔记

## 编译信息

- **软件**: libjxl (JPEG XL image format reference implementation)
- **版本**: 0.11.2
- **编译日期**: 2026-05-21
- **编译状态**: success
- **构建系统**: CMake

## 编译环境

- **操作系统**: OpenHarmony
- **编译器**: Clang 15.0.4
- **CMake**: 4.1.2

## 依赖

### 必需依赖（已安装）
- brotli 1.1.0（预编译包）
- lcms2 2.19（预编译包）
- zlib 1.3.1（预编译包）
- libpng 1.6.43（预编译包）

### 第三方依赖（bundled）
- highway 1.4.0（下载到 third_party/highway）

## 编译配置

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DJPEGXL_ENABLE_SKCMS=OFF \
      -DJPEGXL_ENABLE_VIEWERS=OFF \
      -DJPEGXL_ENABLE_PLUGINS=OFF \
      -DJPEGXL_BUNDLE_LIBPNG=OFF \
      -DJPEGXL_FORCE_SYSTEM_BROTLI=ON \
      -DJPEGXL_ENABLE_SJPEG=OFF \
      -DJPEGXL_ENABLE_OPENEXR=OFF \
      ..
make -j4
make install DESTDIR=$TEST_PREFIX
```

## 编译问题与解决

### 问题1：缺少 Highway 库

**错误信息**：
```
CMake Error: Highway library (hwy) not found.
```

**解决方案**：手动下载 highway 1.4.0 到 third_party/highway 目录。

### 问题2：缺少 LCMS2 库

**错误信息**：
```
CMake Error: Please install lcms2 or run git submodule update --init
```

**解决方案**：安装预编译包 lcms2 2.19。

## 编译产物

### 工具
- cjxl：JPEG XL 编码器
- djxl：JPEG XL 解码器
- jxlinfo：JPEG XL 文件信息工具
- benchmark_xl：性能测试工具

### 库
- libjxl.so：核心库
- libjxl_threads.so：线程支持库
- libjxl_cms.so：色彩管理库
- libhwy.a：Highway SIMD 库

## 打包信息

- **主包**: libjxl-0.11.2-ohos-aarch64.tar.gz (10.18MB)
- **Debug包**: libjxl-0.11.2-ohos-aarch64-debug.tar.gz (1.08MB)
- **外部依赖收集**: 3 个库（brotli, lcms2, png）

## 备注

- 未修改源码，无补丁文件
- Highway 使用 bundled 版本，已打包到预编译包中
- 禁用了可选功能（SKCMS, SJPEG, OpenEXR）以减少依赖