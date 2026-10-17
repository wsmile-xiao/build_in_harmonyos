# DRAFT-jsonifier-neon-cpu-instructions-bits — 库内提交的 CPU 指令集位在 aarch64 需重配

- **严重度**: 2（🟡 medium）
- **类别**: platform, portability, headers
- **触发工具**: clang/clang++（编译阶段）
- **来源库**: jsonifier 0.9.97（OHOS aarch64 适配，2026-09-03）

## 错误特征

```
In file included from .../Config.hpp:123:
/data/.../include/immintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
/data/.../include/xmmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
/data/.../include/hresetintrin.h:42:27: error: invalid input constraint 'a' in asm
```

## 根因分析

上游 tar 包内提交的 CPU 指令集位按 x86 主机生成。jsonifier 的
`JsonifierCPUInstructions.hpp` 提交值为 `38`（= AVX2|LZCNT|BMI），该位组合在
aarch64 编译器下会让 `Config.hpp` 走 x86 SIMD 分支并 `#include <immintrin.h>`/
`<xmmintrin.h>`——这些头仅 x86/x64 可用，aarch64 直接编译失败。此外
`Config.hpp` 的 PREFETCH 宏对 clang 分支**无条件**包含 `<xmmintrin.h>`，同样失败。

## 推荐方案

补丁两处（patches/ 落盘，不改源码语义）：
1. `JsonifierCPUInstructions.hpp`：`#define JSONIFIER_CPU_INSTRUCTIONS 38` → `8`（NEON 位），使 Config.hpp 走 `#elif JSONIFIER_CHECK_FOR_INSTRUCTION(JSONIFIER_NEON)` 分支并包含 `arm_neon.h`。
2. `Config.hpp` PREFETCH：在 `__APPLE__ && __arm64__` 分支后增加
   `#elif defined(__aarch64__) || defined(_M_ARM64)` 分支使用
   `__builtin_prefetch(ptr, 0, 0)`，避免包含 xmmintrin.h。

**验证**: conan create（ohos-aarch64 profile）+ 上游测试 211 用例 + HarmonyOS 专项测试全部通过。

## 适用边界

- 任意 header-only C++ 库落地 OHOS aarch64 时，若内部以 CPU 指令集位宏选择 SIMD 头
- 与 E506（CMake 源选择/链接 undefined symbol 场景）不同：本条目是**库内提交宏 +
  头文件包含路径**场景，为新增差异

## 查重差异（四范围）

| 范围 | 结果 |
|------|------|
| index.tsv / doc/ | E506 相关但场景不同（E506=CMake 源选择，本条目=库内指令集位宏），未命中 |
| graph/*.kv | 无匹配 |
| drafts/ | 无匹配 |

→ **路径 B（知识库扩展）**：随 jsonifier 归档同 PR 交付。
