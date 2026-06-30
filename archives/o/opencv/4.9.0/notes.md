# opencv 4.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-25
- 编译器: clang/clang++ (Clang 15.0.4)
- 目标平台: OpenHarmony
- 状态: built

## 编译步骤

1. **解压源码**: 从本地 Documents 目录获取源码包
2. **创建构建目录**: `mkdir build && cd build`
3. **CMake 配置**:
```bash
cmake \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_NEON:BOOL=OFF \
  -DPNG_ARM_NEON:BOOL=OFF \
  -DCPU_BASELINE_DISABLE=NEON \
  -DWITH_OPENCL=OFF \
  -DWITH_CUDA=OFF \
  -DBUILD_TESTS=OFF \
  -DBUILD_PERF_TESTS=OFF \
  -DBUILD_opencv_apps=OFF \
  -DBUILD_LIST="calib3d,core,dnn,features2d,flann,highgui,imgcodecs,imgproc,ml,objdetect,photo,stitching,video,videoio" \
  ..
```
4. **编译**: `make -j2` (耗时约 15 分钟)
5. **安装**: `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-opencv-4.9.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PNG NEON 链接错误 | CMake 检测处理器为 'unknown'，导致 libpng 的 CMakeLists.txt 中 `ARM OR AARCH64` 条件不满足，`PNG_ARM_NEON_OPT=0` 未被添加 | 修改 `3rdparty/libpng/CMakeLists.txt`，在文件开头强制添加 `add_definitions(-DPNG_ARM_NEON_OPT=0)` |
| 2 | CMake 变量类型错误 | `-DENABLE_NEON=OFF` 被存储为 `UNINITIALIZED` 类型而非 `BOOL` | 使用 `-DENABLE_NEON:BOOL=OFF` 显式指定类型 |

## 源码修改

**文件**: `3rdparty/libpng/CMakeLists.txt`
**修改**: 在第 31 行之前添加以下代码：
```cmake
# Force disable NEON for HarmonyOS cross-compilation (processor detected as 'unknown')
# Original condition: ARM OR AARCH64 - not triggered on HarmonyOS
# Always add PNG_ARM_NEON_OPT=0 to prevent undefined NEON symbols
add_definitions(-DPNG_ARM_NEON_OPT=0)
message(STATUS "libpng: NEON disabled for cross-compilation (PNG_ARM_NEON_OPT=0)")
```

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- Python: 3.12.8

## 验证结果

```bash
# 验证库文件
ls -la /storage/Users/currentUser/tmp/test-install-opencv-4.9.0/storage/Users/currentUser/usr/local/lib/libopencv*

# 输出: 共 14 个模块库，全部编译成功
libopencv_calib3d.so   2.0 MB
libopencv_core.so      3.0 MB
libopencv_dnn.so       6.5 MB
libopencv_features2d.so 778 KB
libopencv_flann.so      678 KB
libopencv_highgui.so    222 KB
libopencv_imgcodecs.so 3.2 MB
libopencv_imgproc.so   3.5 MB
libopencv_ml.so         598 KB
libopencv_objdetect.so 1.1 MB
libopencv_photo.so      666 KB
libopencv_stitching.so  634 KB
libopencv_video.so      526 KB
libopencv_videoio.so    358 KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libopencv_core.so | 3.0 MB | 核心模块 |
| libopencv_imgproc.so | 3.5 MB | 图像处理模块 |
| libopencv_dnn.so | 6.5 MB | 深度神经网络模块 |
| libopencv_imgcodecs.so | 3.2 MB | 图像编解码模块 |
| libopencv_calib3d.so | 2.0 MB | 相机标定模块 |
| 其他 9 个模块 | - | features2d, flann, highgui, ml, objdetect, photo, stitching, video, videoio |

## 注意事项

1. **NEON 禁用是关键**: OpenHarmony 环境下 CMake 无法正确识别处理器类型，必须手动修改 libpng CMakeLists.txt 强制禁用 NEON
2. **CMake 变量类型**: 使用 `:BOOL=OFF` 显式指定布尔类型，避免变量被识别为 `UNINITIALIZED`
3. **编译时间**: 约 15 分钟（-j2 并行编译）
4. **模块选择**: 使用 `-DBUILD_LIST` 指定需要的模块，减少编译时间和产物大小