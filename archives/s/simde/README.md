# SIMDe

SIMDe（SIMD Everywhere）是一个跨架构可移植的 SIMD 指令集头文件库，提供
ARM NEON、x86 SSE/AVX 等指令集的纯 C 可移植实现，开发者可在不支持目标
指令集的平台上编写、编译并运行同一套 SIMD 代码。

- 官方仓库：https://github.com/simd-everywhere/simde
- 版本：0.8.2（正式标签 v0.8.2，commit 71fd833d9666141edcd1d3c109a80e228303d8d7）
- 类型：header-only（无编译产物）
- 许可证：MIT

## 适配说明（HarmonyOS PC / aarch64）

- 直接打包 `simde/` 头文件目录至包内 include；
- 上游 NEON 头文件已在 aarch64 实测通过（test_package 断言 vaddq_s8/vabdq_s16/vceqq_s32 及 SSE2 便携路径）；
- 官方 release tarball 不含 `test/munit` 子模块，本地测试需 manual-download 补充（知识 E150）。
