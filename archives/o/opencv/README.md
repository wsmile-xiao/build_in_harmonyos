# OpenCV

**Open Source Computer Vision Library** — 开源计算机视觉库，提供数百种计算机视觉算法。

## 功能概述

- **核心模块**: core（基础数据结构）、imgproc（图像处理）、imgcodecs（图像编解码）
- **视觉模块**: calib3d（相机标定）、features2d（特征检测）、video（视频分析）
- **高级模块**: dnn（深度神经网络）、stitching（图像拼接）、objdetect（目标检测）

## 适配版本

| 版本 | 打包形式 | 说明 |
|------|----------|------|
| 4.12.0 | conan | 15 个模块，接 conan 依赖 + ffmpeg 视频 I/O，真机 14 条断言全绿 |
| 4.9.0 | 源码构建笔记 | 早期适配记录 |

---

## 4.12.0（conan，推荐）

上游 OpenCV **完全没有鸿蒙支持**（`platforms/` 无 ohos，全树无 `OHOS` 分支），
本配方**不改一行上游源码**，适配全靠 SDK `ohos.toolchain.cmake` + 构建参数。

### 四个必须处理的适配点

1. **SDK 缺 `llvm-ranlib`** — `ohos.toolchain` 把 `CMAKE_RANLIB` 指向 `<SDK>/llvm/bin/llvm-ranlib`，
   而该目录下**只有 `llvm-ar`**。cmake 造静态库走 `AR qc && RANLIB`，于是「`.o` 全编得动、
   一造 `.a` 就报 `Error running link command: no such file or directory`」。
   须 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`。
2. **OpenCV 交叉编译时自行禁用 pkg-config**（顶层 `CMakeLists.txt:704`）——只给
   `PKG_CONFIG_PATH` 不满足豁免，外部库一律探测不到。须给 `PKG_CONFIG_LIBDIR`
   + `-DOPENCV_ENABLE_PKG_CONFIG=ON`。
3. **conan 生成的 `.pc` 版本号会让 ffmpeg 被判过旧** —— `PkgConfigDeps` 写的是 conan 包版本
   `7.1.5`，而 OpenCV 比的是 libav* 的 ABI 版本下限（libavcodec ≥ 54.35.0），
   出现「四个子库全 YES、总判却 NO」。须用 ffmpeg 自带 `.pc` 覆盖。
4. **G-API 的 ADE 拉不到会静默跳过整个 gapi 模块**（既不在 `To be built` 也不在 `Disabled`）。
   须预置到 `<源码>/.cache/ade/<md5>-v0.1.2e.zip`。

细节见 `4.12.0/notes.md`。

### 依赖

走 conan：zlib/1.3.1.1、libjpeg-turbo/3.2.0、libpng/1.6.58、libwebp/1.6.0、
openjpeg/2.5.4、eigen/3.4.0、**ffmpeg/7.1.5**。
走 OpenCV 自带 3rdparty 静态内链：libtiff、protobuf（dnn 用）、quirc、ade。

> 4.9.0 记录的 libpng NEON 问题源自使用**自带** `3rdparty/libpng`；4.12.0 改用 conan
> libpng 后该问题不再出现，无需禁用 NEON。

### 已知限制

- **highgui 为 headless**：无 X11/GTK/Qt/Wayland，`cv::imshow` 等开窗 API 不可用
- 不支持 CUDA/OpenCL；未编入 OpenEXR/Jasper/AVIF/JPEG XL/LAPACK/TBB
- 不产命令行工具，不产 Python/Java/JS 绑定
- **JPEG 2000 只支持 `imwrite`/`imread`**，不支持 `imencode`/`imdecode`
  （OpenCV 的 OpenJPEG 编码器只能建文件流，属上游实现限制）
- 接了 ffmpeg 后产物**不自包含**，消费方须部署整个依赖图

---

## 4.9.0（早期源码构建记录）

### 关键问题
1. **处理器检测失败**: CMake 在 OpenHarmony 上检测处理器为 'unknown'（而非 aarch64），导致 libpng NEON 定义未正确添加
2. **NEON 链接错误**: ARM NEON 优化函数未链接，需手动禁用

### 解决方案
修改 `3rdparty/libpng/CMakeLists.txt`：
```cmake
add_definitions(-DPNG_ARM_NEON_OPT=0)
```

CMake 配置选项：
```bash
-DENABLE_NEON:BOOL=OFF
-DPNG_ARM_NEON:BOOL=OFF
-DCPU_BASELINE_DISABLE=NEON
```

## 编译依赖

- cmake >= 3.10
- clang >= 15.0
- Python >= 3.2（构建脚本）

## 参考资料

- 官网: https://opencv.org
- 源码: https://github.com/opencv/opencv
- 文档: https://docs.opencv.org