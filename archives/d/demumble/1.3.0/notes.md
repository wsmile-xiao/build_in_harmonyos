# demumble 1.3.0 HarmonyOS 适配记录

## 源码与构建

- 官方标签: `v1.3.0`（commit `e82c4520107ab87460c92a65d2b0e8b090b3f742`）
- 官方源码 SHA256: `29501fbd5522820a1672aea0292105b8706899e4e4b283ff51c126f79b3b2c41`
- 构建系统: CMake，C++17
- 第三方依赖: 无；LLVM 与 Swift demangler 已内嵌在官方源码中

## HarmonyOS 适配

上游在非 Apple Unix 平台强制 `-fno-PIC -no-pie`。该设置会使 aarch64 OHOS 链接出现未对齐的 `R_AARCH64_LDST64_ABS_LO12_NC` 重定位。补丁仅在 OHOS 上保留 SDK 的 PIE/PIC 默认值，其他平台保持上游行为。

## 验证

- armv8/aarch64 Conan 构建通过
- x86_64 Conan 构建通过
- 显式 `conan test` 通过
- HarmonyOS 6.0 PC 虚拟机：上游 42/42、消费者 11/11、HMDFS 鸿蒙特有测试 1/1

编译结束。
---

**编译结束**: 2026-09-10 16:23
**最终状态**: built
