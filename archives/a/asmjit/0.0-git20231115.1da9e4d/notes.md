# AsmJit 0.0-git20231115.1da9e4d 适配笔记

## 库概况

- **类型**: C++ JIT 汇编器库（机器码生成）
- **上游**: https://github.com/asmjit/asmjit
- **Commit**: `1da9e4d957fc8c48d1eac68c76c1b139b3691a24`（2023-11-15 快照）
- **License**: Zlib
- **架构支持**: x86/x64 + AArch64（OHOS 需要 AArch64）

## 构建系统

- **CMake 3.5+**，纯 C++11，无外部依赖
- 关键 CMake 选项:
  - `ASMJIT_STATIC` — 静态库（默认 OFF，我们用 ON）
  - `ASMJIT_TEST` — 构建测试（默认 OFF）
  - `ASMJIT_NO_X86` — 禁用 x86 后端
  - `ASMJIT_NO_AARCH64` — 禁用 AArch64 后端
- 系统依赖: `pthread`（非 Win/Android/OHOS）、`rt`（Linux/NetBSD）

## OHOS 注意事项

1. **pthread**: OHOS 使用 bionic（与 Android 同），pthread 内置于 C 运行时，不需要显式链接
2. **rt 库**: 上游 CMakeLists.txt 对 `CMAKE_SYSTEM_NAME` 匹配 `Linux` 或 `NetBSD` 时链接 `rt`；
   OHOS 不匹配此条件，不会链接 rt
3. **cmake_system_name**: 必须设为 `OHOS`（不是 `HarmonyOS`），否则找不到 Platform/OHOS.cmake

## 上游测试

ASMJIT_TEST=ON 时构建以下 CTest 测试:
- `asmjit_test_unit` — 核心单元测试（嵌入模式）
- `asmjit_test_assembler` — 汇编器测试
- `asmjit_test_compiler` — 编译器测试
- `asmjit_test_emitters` — 发射器测试
- `asmjit_test_instinfo` — 指令信息测试
- `asmjit_test_perf` — 性能测试（非 TEST 类型，是 EXECUTABLE）

## 依赖关系

- **上游无 Conan 依赖**
- **下游消费者**: blend2d（已适配 0.21.2）、pdf4qt（已适配 1.5.3.1）
- blend2d 的 manifest.yaml 中已注明依赖 asmjit

## 真机验证结果（2026-08-20）

- **设备**: HarmonyOS PC aarch64, HongMeng Kernel 1.12.0
- **编译器**: clang 15.0.4 (aarch64-unknown-linux-ohos)
- **Conan**: 2.31.1
- **构建**: ✅ 静态库 libasmjit.a + 头文件 + CMake config
- **测试**: ✅ test_package 通过（JIT 函数生成 + 执行 + 返回值验证）
- **产物**: `lib/libasmjit.a`, `include/asmjit/`, `lib/cmake/asmjit/asmjit-config.cmake`

### 遇到并解决的 OHOS 特有问题

1. **CMAKE_SYSROOT 必须显式设置**: `clang-15` 虽有 `.cfg` 文件但 CMake 不一定读取，需在 toolchain 中设置 `CMAKE_SYSROOT` 指向 `~/usr/local/sysroot`
2. **可执行文件代码签名**: OHOS 要求 ELF 二进制经 `binary-sign-tool` 签名后才能执行，否则 "Permission denied"
3. **C++ 运行时需显式链接**: test_package 需 `target_link_libraries(... c++ c++abi)`，否则 undefined symbol: `operator delete`, `__cxa_pure_virtual` 等
4. **JIT 可执行内存**: `mmap` + `PROT_EXEC` 在 OHOS 上正常工作，asmjit JitRuntime 无问题
5. **asmjit API 注意**: `a64::Compiler` 构造时传 `CodeHolder*`（不是 `addCode()`），版本宏是 `ASMJIT_LIBRARY_VERSION`（不是 `ASMJIT_VERSION_MAJOR`）

## 已知风险

- 这是 git snapshot 版本，上游无 release tag
- 上游测试包含 x86 专用测试，在 AArch64 环境下这些会跳过或不需要

## 下一步

1. ✅ 真机 `conan create` 验证 — **已通过**
2. ✅ JIT 可执行内存 — **OHOS 正常支持 mmap PROT_EXEC**
3. 发布到制品仓 ohpcd（需先推送 PR 并合入）
4. 验证下游消费者 blend2d 能否正确链接 asmjit
