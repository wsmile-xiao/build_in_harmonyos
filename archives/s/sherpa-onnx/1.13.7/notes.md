# sherpa-onnx 1.13.7 适配笔记

## 基本信息

- **软件**: sherpa-onnx v1.13.7
- **仓库**: https://github.com/k2-fsa/sherpa-onnx
- **许可证**: Apache-2.0
- **语言**: C/C++ (C++17)
- **构建系统**: CMake
- **功能**: 离线语音合成 (Offline TTS)，通过 SHERPA_ONNX_ENABLE_TTS=ON 启用

## 适配环境

- **平台**: HarmonyOS PC (aarch64-unknown-linux-ohos)
- **编译器**: clang 15.0.4 (aarch64-unknown-linux-ohos)
- **CMake**: 4.1.2
- **CMAKE_SYSTEM_NAME**: HarmonyOS

## 依赖信息

### onnxruntime/1.27.1 (Conan 制品仓)
- 核心ML推理依赖，已通过 conan 制品仓 (ohpcd) 获取
- 通过 SHERPA_ONNXRUNTIME_INCLUDE_DIR 和 SHERPA_ONNXRUNTIME_LIB_DIR 环境变量注入路径
- Include 路径需指向 `include/onnxruntime/` 子目录（代码中 `#include "onnxruntime_cxx_api.h"` 不含前缀）

### CMake FetchContent 子依赖（自动下载）
- kaldi-native-fbank (v1.22.3) + kissfft
- kaldi-decoder (v0.3.0) + kaldifst (v1.8.0)
- simple-sentencepiece (v0.7)
- espeak-ng-for-piper (ed530aa)
- piper-phonemize (f3ff95af)
- openfst (v1.8.5-2026-07-09)
- eigen (5.0.1)
- json (v3.12.0)
- asio (asio-1-24-0)
- websocketpp (b9aeec6)
- cargs (v1.0.3)
- hclust-cpp (2026-02-25)
- pybind11 (v3.0.0)
- googletest (v1.13.0)

这些依赖通过 CMake FetchContent 自动下载，不需要单独适配为 conan 包。

## 编译过程

### CMake 选项（参考上游 build-ohos-arm64-v8a.sh）
```
-DCMAKE_BUILD_TYPE=Release
-DBUILD_SHARED_LIBS=ON
-DSHERPA_ONNX_ENABLE_TTS=ON
-DSHERPA_ONNX_ENABLE_BINARY=OFF
-DSHERPA_ONNX_ENABLE_PYTHON=OFF
-DSHERPA_ONNX_ENABLE_TESTS=OFF
-DSHERPA_ONNX_ENABLE_CHECK=OFF
-DSHERPA_ONNX_ENABLE_PORTAUDIO=OFF
-DSHERPA_ONNX_ENABLE_JNI=OFF
-DSHERPA_ONNX_ENABLE_C_API=ON
-DSHERPA_ONNX_ENABLE_WEBSOCKET=OFF
-DSHERPA_ONNX_ENABLE_SPEAKER_DIARIZATION=OFF
-DBUILD_PIPER_PHONMIZE_EXE=OFF
-DBUILD_PIPER_PHONMIZE_TESTS=OFF
-DBUILD_ESPEAK_NG_EXE=OFF
-DBUILD_ESPEAK_NG_TESTS=OFF
```

### 编译结果
- `libsherpa-onnx-c-api.so` - C API 共享库
- `libsherpa-onnx-cxx-api.so` - C++ API 共享库
- `include/sherpa-onnx/c-api/c-api.h` - C API 头文件
- `include/sherpa-onnx/c-api/cxx-api.h` - C++ API 头文件

## 适配要点

### 1. onnxruntime 路径注入
上游脚本通过 `SHERPA_ONNXRUNTIME_LIB_DIR` 和 `SHERPA_ONNXRUNTIME_INCLUDE_DIR` 环境变量指定 onnxruntime 位置。在 conan 配方中，通过 `generate()` 方法从 conan 依赖获取路径并设置环境变量。

关键点：include 路径需指向 `include/onnxruntime/` 子目录，因为代码中 `#include "onnxruntime_cxx_api.h"` 不含 `onnxruntime/` 前缀。

### 2. GitHub 依赖下载
本项目使用 CMake FetchContent 自动下载子依赖。在某些网络环境下 GitHub 可能不可达，需要：
- 预下载依赖到 `$HOME/Downloads/` 目录（cmake 文件的 `possible_file_locations` 会检查此目录）
- 或使用 GitHub 代理（如 ghfast.top）

### 3. OHOS 平台检测
上游有 `if(CMAKE_SYSTEM_NAME STREQUAL OHOS)` 条件代码。在本设备上 `CMAKE_SYSTEM_NAME` 为 `HarmonyOS`（不是 `OHOS`），但该条件仅添加 `-Wno-unused-command-line-argument` 标志，不影响构建。

### 4. 符号链接问题
源码包中包含指向绝对路径的符号链接（scripts/go/ 目录），Python 3.12 的 tarfile `filter='data'` 会拒绝解压。使用系统 `tar` 命令解压可绕过此限制。

## 编译验证
- `conan create` 成功通过
- 构建产物：libsherpa-onnx-c-api.so, libsherpa-onnx-cxx-api.so
- test_package 测试通过（调用 SherpaOnnxGetVersionStr() 验证 C API）

## 最终状态
编译结束，状态: COMPLETED, status: built
---

**编译结束**: 2026-09-09 15:56
**最终状态**: built
