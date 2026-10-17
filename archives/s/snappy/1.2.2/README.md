# snappy 1.2.2 — OpenHarmony 编译记录

## 基本信息
- 软件: snappy
- 版本: 1.2.2
- 构建系统: CMake
- 目标: ohos-aarch64
- 状态: published (Conan recipe verified)

## 编译指导
```bash
conan create archives/s/snappy/1.2.2/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## CMake 选项
- BUILD_SHARED_LIBS=OFF (静态库)
- SNAPPY_BUILD_TESTS=OFF (禁用测试)
- SNAPPY_BUILD_BENCHMARKS=OFF (禁用基准测试)

## 补丁清单
无补丁，使用 CMake 参数适配平台。

## 已知限制
无平台相关限制。

## 功能验证
test_package/test_snappy.cpp: 使用 snappy C API 压缩/解压字符串，验证往返一致性。
测试输出: "Snappy round-trip OK: compressed 53 -> 55 bytes"
