# DRAFT：fmt/std.h 版本能力矩阵（9.1.0）——消费方测试断言必须钉版本

- **草稿 ID**: DRAFT-fmt-9.1.0-std-h-version-capability-matrix
- **来源库**: fmt 9.1.0（任务 fmt-9.1.0-r01-pc2-10）
- **判定**: 路径 B（知识库扩展候选，新增知识，无正式条目覆盖；.kv/.md 同 stem 配对）

## 问题

fmt 的 `fmt/std.h` 头在不同版本支持的 std 类型 formatter 集合不同。fmt 9.1.0 的
`std.h` 为 `std::filesystem::path`（C++17）、`std::thread::id`、`std::monostate`、
`std::variant` 提供 formatter；**`std::optional` 的 formatter 首次出现于 12.x**，
9.1.0 中 `<fmt/std.h>` 完全不涉及 optional。

若 test_package / 下游消费测试不按目标版本钉定断言，直接照抄 12.x 的断言
（如 `fmt::format("{}", std::optional<double>(1.5))` → `"optional(1.5)"`），
在 9.1.0 上会得到：

```
fmt/core.h:1756:3: error: static assertion failed due to requirement 'formattable':
Cannot format an argument. To make type T formattable provide a formatter<T> specialization
```

本次 fmt 9.1.0 首轮 G2 conan create 实撞此错（test_package 里用 `std::this_thread::get_id()`
格式化且漏包含 `<fmt/std.h>` → `std::__thread_id` 无 formatter）。

## 根因

- fmt 的 `fmt/std.h` 能力随版本增长：9.1.0 支持 thread::id / filesystem::path /
  monostate / variant，`std::optional` 是 12.x 新增；
- 使用 std 类型格式化必须显式 `#include <fmt/std.h>`（thread::id 也不例外）；
- 八进制前缀：fmt 8.x~9.x 的 `{:#o}` 仍是 `"0"` 前缀（8 → `"010"`），`"0o"` 是后版本
  行为——8.1.1 notes 曾推测"0o 是 fmt 9+ 才改"，被 9.1.0 实测证伪
  （format-test.cc 断言 `{0:#o}` 042 → `"042"`，ctest 全过）。

## 方案

写 fmt 消费测试（test_package / 下游 consumer / 上游 ctest 复跑）前核对目标版本：

1. `std::optional` 仅 12.x+ 可格式化；9.x 用 `std::thread::id` / `std::filesystem::path` 代替；
2. 任何 std 类型格式化都显式 `#include <fmt/std.h>`（含 thread::id）；
3. 进制前缀断言（八进制 `"0"` vs `"0o"`、二进制/十六进制大写等）按目标版本实测后钉定，
   不照抄新版文档或旧版 notes 推测；
4. 兼容多版本时用 `FMT_VERSION` 宏（fmt/core.h）分支断言。

## 验证

- fmt 9.1.0（OHOS toolchain clang 15.0.4 / aarch64-unknown-linux-ohos）：
  - G2 conan create test_package：补 `#include <fmt/std.h>` 后 `fmt OK: 9 CHECK passed, FMT_VERSION=90100`；
  - 上游 ctest 20/20 全过（format-test 断言行 `{0:#o}` 042 → `"042"` 通过）；
  - 鸿蒙专项 dlopen 测试 3/3 通过（已签名 libfmt.so.9.1.0 运行时加载 + dlsym + 调用）；
- fmt 12.2.0（既有归档）：`std::optional<double>(1.5)` → `"optional(1.5)"` 实测通过。

## 适用边界 / 反例

- 仅适用于 fmt 库自身及其下游消费方（spdlog、mitama-cpp-result 等）；
- 与 OHOS libc++15 `<format>` 空 stub（DRAFT-ohos-libcxx15-format-ranges-capability-gap）
  是两回事：后者是标准库 `std::format` 不可用，本条目是 fmt 库自身 `fmt/std.h` 版本能力；
- 反例：对 fmt 9.1.0 断言 `optional(1.5)`（12.x 行为）→ 编译失败；对 9.1.0 断言 `0o10` → 断言失败。

## 七轴查重

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无正式条目/草稿描述 fmt/std.h 版本能力矩阵或八进制前缀版本差异 |
| causal_duplicate | 否 | 与 libc++15 <format> stub（std::format 不可用）无因果，根因不同 |
| trigger_overlap | 部分 | 错误签名关键词（formatter/format）与 libc++ stub 类条目重叠，但触发面不同 |
| solution_overlap | 部分 | 都涉及 include/编译探测，但方案核心是"按版本钉断言"，非头文件守卫 |
| combination_novelty | 是 | fmt 版本能力矩阵（thread::id/optional 的分界在 12.x）+ 八进制前缀实测证伪 8.1.1 推测 |
| boundary_novelty | 是 | 明确 9.1.0 支持集合与 12.x 差异边界、显式 include 要求、前缀版本钉定 |
| test_migration_novelty | 是 | 断言迁移必须钉版本；FMT_VERSION 分支兼容写法 |

## 关系

- similar_to: DRAFT-ohos-libcxx15-format-ranges-capability-gap（关键词部分重叠，无覆盖）
- caused_by / prerequisite_of / conflicts_with: 无

## 复用决定

- 正式知识（index.tsv）：未命中 → 新建草稿；
- 图谱：未命中 → 新建草稿；
- 草稿库：无同内容草稿 → 新建；
- 既有 8.1.1 notes 的"0o 是 fmt 9+ 才改"推测被本条目修正（9.1.0 实测仍为 "0" 前缀）。
- 决定: new_draft（路径 B），PR 前缀【知识库扩展】
