# libpog 0.5.3 — HarmonyOS PC 适配说明

## 概况

libpog 是 C++17 的 LALR(1) 解析器生成库：把解析器拆成① token 声明（RE2 正则）与
② token 上的文法规则，生成 LALR(1) 解析表/解析器。

- 上游：https://github.com/metthal/pog （源码取自 Debian orig tarball）
- 形态：**header-only**（`include/pog/**`，CMake INTERFACE 目标 `pog`）
- 依赖：`re2/2024-04-01`（tokenizer）、`fmt/8.1.1`（诊断/报告）——均来自制品仓
- 许可证：MIT

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 本体 header-only，但依赖 RE2/fmt | `package_type="header-library"`；`requirements()` 引入 `re2/2024-04-01`、`fmt/8.1.1`；`package_info().requires=["re2::re2","fmt::fmt"]` 传播 |
| 2 | 上游自带 `cmake/Findre2.cmake`、`cmake/fmt/Findfmt.cmake`（module 模式，会先命中） | 设 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，强制 `find_package(re2/fmt)` 走 Conan 的 config 包，得到 `re2::re2`/`fmt::fmt` |
| 3 | 上游 `deps/` 用 ExternalProject 从自带源码构建 re2/fmt（bundled 模式） | **不用** bundled，直接用制品仓已构建的 re2/fmt（更快、更可控） |
| 4 | 上游 `project(... VERSION 0.5.2)` 与 tarball 0.5.3 不一致 | 仅影响上游自带 `pog-config-version.cmake`；Conan 包版本取 0.5.3（任务/tarball） |
| 5 | 上游测试 | `POG_TESTS=ON`，用随包 googletest 构建 `pog_tests` 并在真机运行 |

## 测试

### 上游

`tests/*.cpp` 共 **132** 个 `TEST`/`TEST_F` 宏（取数：
`grep -cE '^\s*TEST(_F)?\s*\(' tests/*.cpp | awk -F: '{s+=$2} END{print s}'`），
经随包 `tests/googletest` 构建为 `pog_tests`。`build()` 在真机运行该可执行文件，
要求全部通过（132/132）。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_libpog.cpp` 共 9 条断言：

- `pog::Symbol<int>`：索引/名字往返、Nonterminal/Terminal/End 的 kind 判定、默认无优先级、
  `set_precedence` 后 `get_precedence()` 往返
- `RE2::FullMatch("aaab", /a+b/)` 命中与不命中 → 证明 **re2 依赖被正确链接**
- `fmt::format("v={}", 42) == "v=42"` → 证明 **fmt 依赖被正确链接**

消费者只链接 `pog::pog`，即可解析 `<pog/...>`、`<re2/re2.h>`、`<fmt/...>`
（依赖由 `cpp_info.requires` 传播）。

## 已知限制

- 仅验证头文件/依赖可用与基础 API；未对生成的 LALR 解析器做端到端解析示例。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
