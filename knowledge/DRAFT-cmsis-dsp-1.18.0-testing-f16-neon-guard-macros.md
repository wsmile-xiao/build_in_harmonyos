# CMSIS-DSP Testing 框架 F16 NEON 套件编译需命令行注入守卫宏

- **草稿 ID**: DRAFT-cmsis-dsp-1.18.0-testing-f16-neon-guard-macros
- **来源**: cmsis-dsp 1.18.0 R02 返工（test 目标链接失败 → 守卫宏注入）
- **分类**: build-system / cmake / testing / DSP / NEON / F16 / guard-macros / toolchain
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 cmsis-dsp 归档同 PR 交付）

## 问题 / 错误签名

- **错误输出**（test 目标链接）:
  ```
  ld.lld: error: undefined symbol: vtable for TransformNeonCF16
  ld.lld: error: undefined symbol: TransformNeonCF16::test_cfft_f16()
  clang-15: error: linker command failed with exit code 1
  ```

## 根因

1. `TransformNeonCF16.cpp` 顶部守卫
   `#if defined(ARM_MATH_NEON_FLOAT16) && defined(ARM_FLOAT16_SUPPORTED)` **在 include 前求值**；
   `ARM_MATH_NEON_FLOAT16` 的自动定义（arm_math_types.h 158-161 行）发生在 include 之后，
   编译单元入口处尚未定义 → 守卫为假 → 整个类方法体被条件编译排除（obj 仅 832 字节）。
2. `ARM_FLOAT16_SUPPORTED` 依赖 `__ARM_FP16_FORMAT_IEEE`（`-march=armv8.2-a+fp16fml` 提供），
   但若仅在命令行定义该宏，会与 `arm_math_types_f16.h` 的重复定义触发 `-Werror -Wmacro-redefined`。
3. Testing/CMakeLists.txt 未通过 target_compile_definitions 传递上述守卫宏 → 链接缺符号。

## 最小修复方案

在 Testing 构建的 C/CXX 编译标志中注入（不改上游源码）:
```
-DARM_MATH_NEON_FLOAT16 -DARM_FLOAT16_SUPPORTED -Wno-macro-redefined
```
- `ARM_MATH_NEON_FLOAT16` + `ARM_FLOAT16_SUPPORTED` 使守卫通过、类方法实例化
- `-Wno-macro-redefined` 抑制与 arm_math_types_f16.h 的重复定义警告（被 -Werror 拦截）
- 注入后 `make` 链接成功（100% Built target test），NEON 配置 786 项实际运行

## 验证结果

| 环境 | 结果 |
|------|------|
| 修复前（无注入） | 链接失败: undefined symbol vtable for TransformNeonCF16（obj 832 字节=空类） |
| 注入双宏 + -Wno-macro-redefined | 链接成功（100% Built target test） |
| NEON 配置运行 | 786 执行 / 606 通过 / 180 失败（后者为 C3 所述独立因子5 缺陷） |

## 适用范围 / 边界

- 适用: 任何在 aarch64 OHOS / clang 15 上构建 CMSIS-DSP Testing 框架并启用 NEON+F16 套件的任务。
- 边界: 仅构建 F16（非 NEON）套件时无此问题（BasicTestsF16.cpp 无顶部守卫）；仅 NEON 无 F16 时也无此问题。
  本缺陷特定于 F16+NEON 组合套件（TransformNeonCF16 / BinaryTestsNeonF16）。

## 禁止策略

- ❌ 删除 F16 NEON 测试类 / 跳过 TransformNeonCF16 来"通过"链接。
- ❌ 把可修的守卫宏缺失写成外部阻塞。
