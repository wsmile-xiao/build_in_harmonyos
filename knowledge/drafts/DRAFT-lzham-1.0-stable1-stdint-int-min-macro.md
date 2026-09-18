# DRAFT-lzham-1.0-stable1-stdint-int-min-macro — musl stdint.h 宏与旧 C++ 自声明常量冲突

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-08
> **Severity**: 🟡 medium | **Category**: compat / libc / headers / macros / portability

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E133**（musl 头遮蔽） | 正式收录 | -isystem 使 musl libc 头遮蔽编译器内建头（stddef/stdlib/pthread） | 非本题——那是**头文件搜索路径遮蔽**，本条目是 **stdint.h 宏与自声明常量同名冲突**，触发点（expected unqualified-id）、修复（#undef 守卫）均不同 |
| **E082**（gnulib conftest） | 正式收录 | configure 运行时探测失败 | 非本题——构建系统探测，与编译期宏冲突无关 |

> 全库查证（2026-09-08）：`INT32_MIN` / `INT8_MIN` / `undef.*_MIN` / `expected unqualified-id` 在 graph 与 drafts 中命中 0 条相关因果；本条目为真增量（lzham 上游仅覆盖 Apple/BSD，OHOS 平台边界为新增）。

## Scope（何时用）

在 OHOS / HarmonyOS（musl）上编译**自声明 `INT8_MIN`/`INT16_MIN`/`INT32_MIN`/`INT32_MAX`/`INT64_MIN`/`INT64_MAX`（或 UINTxx_MIN/MAX）等标准宏同名常量**的旧 C/C++ 库（2015 年前后 C++03 代码常见）时，若出现：

- 编译报 `expected unqualified-id` / `expected ')'`，错误行指向 `const int32 INT32_MIN = ...` 之类声明；
- 编译器 note 显示 `expanded from macro 'INT32_MIN'`（stdint.h）；
- 同一源码在 glibc 环境正常（glibc C++03 下不展开这些宏或行为不同）。

典型实例：lzham 1.0-stable1（`lzhamdecomp/lzham_types.h`）。

## Symptom

```text
lzham_types.h:60:16: error: expected ')'
/.../sysroot/usr/include/stdint.h:40:21: note: expanded from macro 'INT32_MIN'
#define INT32_MIN  (-1-0x7fffffff)
lzham_types.h:61:16: error: expected unqualified-id
   const int32 INT32_MAX = 2147483647;
```

## Root Cause

1. musl 的 `stdint.h` 将 `INT8_MIN`...`INT64_MAX` 等定义为宏（`#define INT32_MIN (-1-0x7fffffff)` 等）。
2. 2015 年代 C++ 库（如 lzham）在 namespace 内自声明 `const int32 INT32_MIN = ...` 等常量。
3. 预处理先展开宏，声明退化为 `const int32 (-1-0x7fffffff) = ...`，语法非法。
4. lzham 上游已为 Apple/FreeBSD/NetBSD 提供 `#undef` 守卫，但未覆盖 OHOS（musl 同样定义这些宏）。

## Fix

`lzham_types.h`（或等价头文件）平台守卫追加 `__OHOS__`，在常量声明前 `#undef` 同名宏：

```c
#if defined(__APPLE__) || defined(__FreeBSD__) || defined(__NetBSD__) || defined(__OHOS__)
   #undef INT8_MIN
   #undef INT8_MAX
   ...
   #undef INT64_MAX
#endif
```

与上游 Apple/BSD 处理完全同构，改动 1 行。

## Verification

- 修复前：`cmake --build <ohos-build>` 报 `lzham_types.h: expected unqualified-id`。
- 修复后：`conan create archives/l/lzham/1.0-stable1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` 构建成功；上游测试 1/1 通过。

## Boundary / 反例

- 使用标准 `<cstdint>` / `<stdint.h>` 且不自声明同名常量的新代码不触发。
- glibc C++ 模式下（若该环境不展开宏）不触发；是否触发取决于 libc 头实现。
- **不可**删除常量声明行——这些常量被 `int_traits` 等模板引用，删除改变语义。

## Relation

- similar_to: [E133]（musl 头相关；问题层不同：宏冲突 vs 头遮蔽）
- caused_by / prerequisite_of / conflicts_with: 无