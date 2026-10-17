# libbsc

## 简介
高性能块排序（block-sorting）数据压缩库，实现基于 BWT 变换的压缩算法家族（ST 等），附带 `bsc` 命令行工具。Apache-2.0 许可。

## OHOS 适配
- 上游原生支持 AArch64：platform.h 将 `__aarch64__` 映射到 `LIBBSC_CPU_FEATURE_A64`，x86 cpuid/xgetbv asm 在 A64 下完全编译排除（`#if LIBBSC_CPU_FEATURE >= SSE2` 守卫，A64=1 < SSE2=2），无源码补丁（路径 A）
- `BSC_ENABLE_NATIVE_COMPILATION=OFF`：禁用 `-march=native`，避免构建机 CPU 特定指令进入其他 OHOS 设备
- `BSC_ENABLE_OPENMP=OFF`：OHOS SDK 不带 libomp，单线程模式为默认交付（设备实测 round-trip 通过）；保留 openmp option 备未来启用
- DT_SONAME 经工具链变量注入（E322/libharu 模式）：上游目标无 SOVERSION，配方设置 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` + `CMAKE_PLATFORM_NO_VERSIONED_SONAME`
- 上游无自动化测试（无 enable_testing/add_test），官方验证方式为 README 手工 CLI round-trip；已列入 no_official_test 白名单，test_package 提供完整覆盖

## 依赖
- 无（可选 OpenMP：OHOS SDK 未提供，默认关闭）

## 功能验证
```bash
# 库 API round-trip（compress→decompress→memcmp 字节级一致）
# CLI round-trip: bsc e in.txt out.bsc && bsc d out.bsc out.txt
```

## 参考
- 上游: https://github.com/IlyaGrebnov/libbsc
