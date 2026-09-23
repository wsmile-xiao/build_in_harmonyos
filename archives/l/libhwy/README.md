# libhwy

## 简介

Google Highway：高性能可移植 SIMD/向量内联函数库。
提供一套 C++ API 编写向量化代码，覆盖标量、x86、Arm、RISC-V、
PowerPC、WebAssembly 等目标；HarmonyOS PC（aarch64）下自动选用 NEON 路径。
conan-center 生态中的规范包名为 `libhwy`（CMake 包名 `hwy`，target `hwy::hwy`）。

## OHOS 适配

- **版本**：1.3.0（与本仓 `archives/h/highway` 同源同版本，产物二进制兼容）
- **构建**：CMake；`CMAKE_SYSTEM_NAME=Linux` 选中 Linux/NEON 分支；
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过部分 worker 缺 libxml2 的检测链接问题
- **依赖**：零运行时依赖；仅链接系统库 `m`、`pthread`
- **测试**：`HWY_TEST_STANDALONE=ON`，上游 CTest 套件默认随 `conan create` 运行，
  不下载 googletest；test_package 做 7 项 SIMD 消费者检查

## 依赖

无。
