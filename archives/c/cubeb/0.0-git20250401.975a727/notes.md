# cubeb 0.0-git20250401.975a727 适配笔记

## 编译环境
- 构建系统: CMake (project version 0.0.0)
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

```bash
# 源码: GitHub archive 975a727e5e30 (2025-04-01 git snapshot)
# SHA-256: 39f55e74ea30686e927d47a389247fd0c3a81691bff3fa7b32d8ddcd8a81feaf

# CMake 构建配置
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_RUST_LIBS=OFF \
  -DBUILD_TESTS=OFF \
  -DLAZY_LOAD_LIBS=ON \
  -DUSE_SANITIZERS=OFF \
  -DBUILD_TOOLS=OFF \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++

cmake --build build -j2
cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无音频后端匹配 | OHOS 平台无 pulse/alsa/jack/sndio/oss 等音频子系统头文件 | LAZY_LOAD_LIBS=ON 默认开启，运行时 dlopen 加载；无后端时库仍可编译，cubeb_init 返回 CUBEB_ERROR |
| 2 | USE_SANITIZERS 需要 sanitizers-cmake 子模块 | git archive 不含子模块 | 设 USE_SANITIZERS=OFF 禁用 |
| 3 | BUILD_TESTS 需要 GTest 子模块 | git archive 不含 googletest 子模块 | BUILD_TESTS=OFF（conan option build_tests=True 时从 conan 引入 gtest/1.17.0） |

## 源码修改

无源码修改。cubeb 的 CMake 构建系统通过 check_include_files 自动检测平台音频后端，在 OHOS 上不匹配任何后端是预期行为。

## 依赖版本

- CMake: 4.1.2
- clang: 15.0.4
- 内置 speex resampler（subprojects/speex/，无需外部依赖）
- Threads::Threads（pthread，OHOS 系统提供）
- DL_LIBS（dlopen，OHOS 系统提供）

## 验证结果

```bash
# test_package 验证 cubeb API 可链接可调用
conan create . --build=missing  # conan-verify G2
# test_cubeb 验证 cubeb_init/cubeb_get_min_latency/cubeb_get_preferred_sample_rate API
```

## 注意事项

- cubeb 在无音频设备的 OHOS 上 cubeb_init 返回 CUBEB_ERROR 是预期行为
- LAZY_LOAD_LIBS=ON 意味着音频后端库在运行时通过 dlopen 加载，编译时不需要
- 内置 speex resampler 编译为 OBJECT library，链接进 cubeb 静态库
- BUILD_TESTS=ON 需要从 conan 引入 gtest（OHOS 制品仓有 gtest/1.17.0）
---

**编译结束**: 2026-09-12 13:16
**最终状态**: built
