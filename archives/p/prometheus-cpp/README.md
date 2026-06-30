# prometheus-cpp

C++ 库，用于将 Prometheus 指标暴露给 Prometheus 监控系统。

## 功能概述

- **Core 模块**：提供 Counter、Gauge、Histogram、Summary、Info 等指标类型的定义、注册和收集
- **Pull 模块**：内嵌 Civetweb HTTP 服务器，通过 `/metrics` 端点暴露 Prometheus 文本格式指标
- **Push 模块**：支持将指标推送到 Prometheus Pushgateway（需 curl 依赖）
- **Compression**：支持 zlib 压缩指标响应（需 zlib 依赖）
- **文本序列化**：将指标序列化为 Prometheus exposition format
- **pkg-config 支持**：生成 prometheus-cpp-core.pc 和 prometheus-cpp-pull.pc

## OHOS 适配

- **必须静态编译**：OpenHarmony 不支持 RUNPATH 加载共享库(.so)，必须使用 `BUILD_SHARED_LIBS=OFF` 编译为静态库(.a)（R4补充铁律）
- **cmake 平台检测**：需设置 `CMAKE_SYSTEM_NAME=Linux`，cmake 没有 OHOS/OpenHarmony 的系统定义
- **Push 模块**：依赖 curl，若 curl 不可用则需用 `ENABLE_PUSH=OFF` 禁用；Core 和 Pull 模块不受影响
- **压缩功能**：依赖 zlib，若 zlib 不可用则需用 `ENABLE_COMPRESSION=OFF` 禁用
- **构建系统识别**：init-build 的 `_guess_build_system()` 可能因 URL 中不含"cmake"关键词而误识别为 autotools，需手动修正为 cmake
- **SSL 下载问题**：HarmonyOS 环境下从 GitHub 下载可能遇到 SSL 证书验证失败，需用 `curl -kL` 手动下载
- **无源码修改**：prometheus-cpp 源码在 OpenHarmony 上可直接编译，无需补丁

## 依赖关系

### 编译依赖
- pthread（系统自带）
- googletest/googlemock（内嵌于 submodules tarball，仅用于测试）

### 可选依赖
- curl：Push 模块所需（如不可用，用 `ENABLE_PUSH=OFF` 禁用）
- zlib：Compression 功能所需（如不可用，用 `ENABLE_COMPRESSION=OFF` 禁用）

### 运行依赖
- pthread

## 已编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.3.0](./1.3.0/) | published | 2026-06-02 |

## 参考资料

- 官网: https://github.com/jupp0r/prometheus-cpp
- 源码: https://github.com/jupp0r/prometheus-cpp/releases/download/v1.3.0/prometheus-cpp-with-submodules.tar.gz
- 许可证: Apache-2.0
