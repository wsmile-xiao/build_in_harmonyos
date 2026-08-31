# crc32c

## 简介
crc32c 是 Google 实现的 CRC32C（Castagnoli CRC32）校验算法库，支持 SSE4.2 和 ARM64 CRC32C 硬件加速指令，并提供可移植的软件回退实现。

## OHOS 适配
- 使用 CMake 构建
- 需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x
- 设置 `-DCRC32C_USE_GLOG=OFF` 禁用可选的 glog 依赖
- 设置 `-DCRC32C_BUILD_TESTS=OFF` 和 `-DCRC32C_BUILD_BENCHMARKS=OFF` 禁用测试和基准（依赖 googletest/benchmark 子模块）
- 设置 `-DCRC32C_INSTALL=ON` 启用安装目标
- ARM64 CRC32C 硬件加速通过 `arm_acle.h` 内建函数支持
- SSE4.2 硬件加速通过 `nmmintrin.h` 内建函数支持
- 两者均不可用时回退到可移植的软件实现

## 排除与替代
无。

## 依赖
无外部依赖。CRC32C_USE_GLOG=OFF 禁用可选的 glog 依赖。

## 功能验证
```bash
# test_package 调用 crc32c::Crc32c, crc32c::Extend, crc32c_value API
# 验证 C/C++ API 一致性和 Extend 部分计算一致性
```

## 参考
- 官网: https://github.com/google/crc32c
