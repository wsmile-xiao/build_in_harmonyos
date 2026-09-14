# SIMDe

SIMDe（SIMD Everywhere）是一个跨架构可移植的 SIMD 指令集头文件库，提供
ARM NEON、x86 SSE/AVX、WebAssembly SIMD、MIPS MSA 等指令集的纯可移植实现，
开发者可在不支持目标指令集的平台上编写、编译并运行同一套 SIMD 代码。

- 官方仓库：https://github.com/simd-everywhere/simde
- 版本：0.8.2（标签 v0.8.2）、0.8.4-rc3（标签 v0.8.4-rc3）
- 类型：header-only（无编译产物）
- 许可证：MIT

## 适配说明（HarmonyOS PC / aarch64）

- 直接打包 `simde/` 头文件目录至包内 include（472 个头文件，与上游逐字节一致）；
- OHOS aarch64 上 simde 正确探测原生 NEON（`SIMDE_ARM_NEON_A64V8_NATIVE`），
  原生别名层（`SIMDE_ENABLE_NATIVE_ALIASES`）与 `simde_` 前缀接口结果一致，
  且消费者 ELF 中确认生成真实 NEON 向量指令（`add v0.16b` / `smax v0.4s` / `mul v0.8h`）；
- 上游 `test/` 的 meson 注册入口全部带 `-DSIMDE_TEST_BARE`，不使用 munit 子模块；
  官方 release tarball 中 `test/munit/` 为空目录，但全量上游测试仍可直接运行（E150 等价命中）；
- 版本 0.8.4-rc3 为上游预发布标签，项目内 meson 声明版本为 0.8.4（API 面与 0.8.4 一致）。
