# jsonifier 0.9.97 知识候选台账（knowledge_candidate_ledger）

适配过程中收集的全部非噪声知识候选，逐项记录真实错误、根因、修复、验证、
适用范围与四范围查重（knowledge/graph/index.tsv + doc/ 正式条目、knowledge/drafts/ 草稿）结果。

## 候选台账

| # | 候选主题 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 四范围查重 | 路径判断 |
|---|---------|---------|------|------|------|----------|-----------|---------|
| C1 | header-only 库提交的 CPU 指令集位须按 aarch64 重配（x86 AVX 位 → NEON） | aarch64 编译含 JsonifierCPUInstructions.hpp 时报 `This header is only meant to be used on x86 and x64 architecture`（immintrin.h） | 上游 tar 内提交的指令集位 38=x86(AVX/LZCNT/BMI)，aarch64 编译器无法包含 immintrin.h | 补丁改为 8(NEON)；配套 Config.hpp PREFETCH 增加 `__aarch64__` 分支用 `__builtin_prefetch` 而非无条件 `#include <xmmintrin.h>` | conan create + 上游测试 211 用例 + 专项测试全部通过 | 任意 cpp header-only 库在 OHOS aarch64 落地；x86 指令集检测宏（类似 ITS-Like CPU instructions 位图） | index/doc：E506 相关（arm_neon 源选择，CMake 链接场景）但场景不同——本候选是"库内提交的指令集位宏 + 头文件包含路径"，非 CMake 源选择；drafts 无 | **路径 B**（新增差异：补丁改写指令集位宏 + PREFETCH 分支） |
| C2 | OHOS libc++ 缺失标准 `<memory_resource>` 与 `<source_location>` | 编译报 `'memory_resource' file not found` / `'source_location' file not found` | OHOS SDK libcxx-ohos（clang-15）未提供这两个标准头 | `<memory_resource>` 用 `__has_include` 守卫；`<source_location>` 提供 API 等价的 Compat shim 头 | 补丁后 conan create + 全测试通过 | 任意依赖 C++17 `memory_resource`/C++20 `source_location` 的库在 OHOS 落地 | index/doc：E130 相关（libcxx-ohos 标准库 C++17 适配）但只是"变更 -std"层面，未覆盖具体缺失头；drafts 无 | **路径 B**（新增差异：具体缺失头清单 + shim 实现形态） |
| C3 | aarch64 默认 unsigned char 导致 C++ 模板部分特化歧义 | `error: ambiguous partial specializations of 'char_traits<const char>'` | aarch64 char 默认 unsigned，`uint8_type` 概念（sizeof==1 && unsigned_integral）对纯 char 成立，与 `not_uint8_t` 特化重叠 | uint8_type 特化追加 `requires (!std::same_as<unwrap_t<T>, char>)` 排除纯 char | 补丁后全测试通过（含 59 int + 43 uint 用例） | 任意 C++ 库以 char/uint8 分派模板特化且目标 char 为 unsigned | index/doc：E419 相关（plain char signedness，但为 C 语言/-fsigned-char 层面），未覆盖 C++ 模板特化歧义；drafts 无 | **路径 B**（新增差异：C++ 模板部分特化 requires 约束修复） |
| C4 | clang-15 对 P0634 typename 省略支持不足 | `error: missing 'typename' prior to dependent type name 'map_simd<N>::type'` | OHOS SDK clang 15.0.4 未完整实现 P0634R3 | 别名模板依赖类型名补显式 `typename` | 补丁后全测试通过 | 任意 C++20 库在 clang-15 编译 | index/doc：**E397 已完整覆盖**（同错误特征、同三个修复模式）；drafts 无 | **路径 A**（完整重复，复用 E397） |

## 路径决定

- C4 完整重复 → 路径 A（复用现有知识 E397，不建草稿）。
- C1/C2/C3 已验证、可在跨库场景复用、查重为未命中或部分覆盖且存在新增差异 → **路径 B（知识库扩展）**：
  需为 C1/C2/C3 建立同 stem 的 `.md`/`.kv` 草稿（knowledge/drafts/，new_draft），并与 jsonifier 归档文件同 PR 交付；PR 前缀将在草稿配对通过后由【依赖项】改为【知识库扩展】（任务头规则：仅 new_draft 且 .md/.kv 配对通过时改前缀）。

## 排除项（噪声，不建知识）

- validateJson 数字路径缺陷（上游 consumeSign 缺陷，非 OHOS 相关，属上游缺陷台账）
- std::map 序列化缺尾 `}`（上游 0.9.97 缺陷，双工具链复现，非适配知识）
- clang-15 IRGen 段错误（工具链 bug，非库缺陷）
- RoundTrip 组指针成员哈希构造失败（上游哈希表限制，非适配知识）