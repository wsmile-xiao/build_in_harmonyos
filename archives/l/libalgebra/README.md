# libalgebra

libalgebra（[官方仓库](https://github.com/mklarqvist/libalgebra)）是一个
**header-only** 的 C/C++ 位/字节统计库（Apache-2.0），提供硬件友好的
SIMD 优化实现与非 x86 回退路径：

- `STORM_popcount64` / `STORM_POPCOUNT` — 64 位 popcount
- `STORM_intersect_count` / `STORM_union_count` / `STORM_diff_count` — 位图交/并/差统计
- `STORM_pospopcnt_u16` — 16 位数组按位位置计数
- `STORM_aligned_malloc` / `STORM_aligned_free` — 对齐内存管理

## OHOS 适配（1.1.0）

- **构建系统**：header-only，无编译产物；Conan 配方按 header-library 打包头文件
- **关键补丁**：`libalgebra.h` 无条件包含 `<x86intrin.h>`，在 aarch64 (OHOS)
  编译失败——补丁 0001 以 X86_OR_X64 家族宏守卫（与头文件既有平台分支一致），
  使头文件在 aarch64-unknown-linux-ohos clang 15 下可用
- **上游测试**：上游 v1.1.0 无测试框架/独立用例；`benchmark.cpp` 为 x86 专用
  基准样例（CPUID/rdtsc），aarch64 不可编译，不作为用例计数（见各版本
  `reports/test-ledger.md` 双口径台账）
- **验证**：消费者用例 + HarmonyOS 专项测试经 conan create 真实运行通过（ctest 2/2）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.1.0 | built | 首轮适配（header-only 打包 + x86intrin 守卫补丁） |