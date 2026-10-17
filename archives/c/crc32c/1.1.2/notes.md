# crc32c 1.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang
- 状态: built

## 编译步骤
```bash
source .build-context-crc32c-1.1.2
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCRC32C_BUILD_TESTS=OFF \
  -DCRC32C_BUILD_BENCHMARKS=OFF \
  -DCRC32C_INSTALL=ON \
  -DCRC32C_USE_GLOG=OFF
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 不支持 cmake_minimum_required(VERSION 3.1) | 版本兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 (通过 tc.cache_variables 注入) |
| 2 | 可选 glog 依赖 | 默认 CRC32C_USE_GLOG=ON 会拉取 glog 子模块 | 设置 CRC32C_USE_GLOG=OFF 禁用 |
| 3 | 测试和基准依赖 googletest/benchmark 子模块 | 默认开启 | 设置 CRC32C_BUILD_TESTS=OFF, CRC32C_BUILD_BENCHMARKS=OFF |

## 源码修改
无补丁。

## 依赖版本
无外部依赖。

## 验证结果
- test_package 调用 crc32c::Crc32c, crc32c::Extend, crc32c_value API
- 验证 C++ API 与 C API 结果一致性
- 验证 Extend 部分计算与完整计算一致性

## 交付物
- libcrc32c.a / libcrc32c.so
- crc32c/crc32c.h

## Conan 配方要点
- cmake_file_name = "Crc32c"
- cmake_target_name = "Crc32c::crc32c"
- libs = ["crc32c"]
- C++11 最低标准
- 无 requires（无依赖）
- settings.os 支持检查使用 in ("Linux", "OHOS", ...) 而非 == "Linux" (R32)
- test_package 实质调用 crc32c API (R34)
---

**编译结束**: 2026-08-27 23:22
**最终状态**: built
