# CMSIS 家族库免 CMSIS-Core 的 standalone 构建模式（HOST=ON → __GNUC_PYTHON__）

- **草稿 ID**: DRAFT-cmsis-dsp-1.18.0-standalone-no-cmsis-core-gnuc-python
- **来源**: cmsis-dsp 1.18.0 HarmonyOS PC 适配（CMake standalone 构建 + Conan 打包）
- **分类**: build-system / cmake / conan / cross-compile / DSP / CMSIS / OHOS
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 cmsis-dsp 归档同 PR 交付）

## 问题 / 错误签名

- **错误输出**（G2/conan create 与裸 clang 消费者编译首错）:
  ```
  arm_math_types.h:126:10: fatal error: 'cmsis_compiler.h' file not found
  #include "cmsis_compiler.h"
  ```
- **复现**: 任何 standalone（无 CMSIS-Core 提供 cmsis_compiler.h）环境构建 CMSIS-DSP——
  源码树只含 DSP 库本体，`Include/arm_math_types.h` 无条件引用 `cmsis_compiler.h`。

## 根因

1. **CMSIS-DSP 头依赖 CMSIS-Core 的 `cmsis_compiler.h`**：`arm_math_types.h` 中
   `#ifndef DOXYGEN #include "cmsis_compiler.h" #endif`，无 CMSIS-Core 时该头不存在。

2. **上游唯一免 CMSIS-Core 开关是 `__GNUC_PYTHON__`**：源码注释明示
   "It is the only way to build on a target not supported by CMSIS Core"；
   `configDsp.cmake` 在 `HOST=ON` 时向 CMSISDSP 目标注入 `PUBLIC __GNUC_PYTHON__`
   （`if (HOST) target_compile_definitions(${project} PUBLIC __GNUC_PYTHON__)`）。

3. **宏必须传播到消费者**：`__GNUC_PYTHON__` 是 PUBLIC 定义，安装的 CMake 包通过
   INTERFACE_COMPILE_DEFINITIONS 传播；Conan 配方若不写 `cpp_info.defines`，消费者
   （含 test_package）编译安装头时仍报 `cmsis_compiler.h not found`。

## 最小修复方案

1. **配方 `generate()`**：`tc.variables["HOST"] = "ON"`（触发 __GNUC_PYTHON__）、
   `tc.variables["CMSISDSP_INSTALL"] = "ON"`、`NEON=ON`（aarch64 原生支持）。
2. **配方 `package_info()`**：`self.cpp_info.defines = ["__GNUC_PYTHON__"]`（等价上游
   INTERFACE_COMPILE_DEFINITIONS，让消费者与 test_package 免 CMSIS-Core 编译）。
3. **test_package/消费者**：仅用公开头 `arm_math.h` + `libCMSISDSP.a` 编译链接运行，
   调用公开 API（arm_dot_prod_f32/arm_sqrt_f32/arm_mean_f32/arm_rms_f32 等）数值断言。

## 验证结果

| 环境 | 结果 |
|------|------|
| 修复前（无 HOST/无 defines） | CMake build 与 test_package 均报 cmsis_compiler.h not found（G2 FAIL） |
| generate() HOST=ON | libCMSISDSP.a 构建成功（660 个 C 源，100% 链接） |
| package_info defines 传播 | conan-verify G2 PASS；test_package 3 API 断言 PASS；消费者 arm_rms_f32 PASS；鸿蒙专项 8 断言 PASS |
| 上游测试 | 默认配置 1527/1527、F16 304/304 通过（见台账） |

## 适用范围 / 边界

- 适用: CMSIS-DSP 及同族（CMSIS-NN 等依赖 CMSIS-Core 头的库）在 OHOS PC / x86 host /
  非 Cortex-M 工具链的 standalone 构建与 Conan 打包。
- 边界: 若目标平台确需 Cortex-M 内核内建函数（NEON/MVE intrinsics 之外的 Core 内建），
  需评估是否真可免 CMSIS-Core；有真 CMSIS-Core 依赖时应打包 cmsis-core 而非绕过。

## 禁止策略

- ❌ 伪造空 `cmsis_compiler.h` 掩盖依赖缺失。
- ❌ 把 standalone 构建失败标成外部阻塞（上游有官方开关，属可修问题）。
- ❌ 消费者编译不带 `__GNUC_PYTHON__` 就宣称通过（真实环境即失败）。
