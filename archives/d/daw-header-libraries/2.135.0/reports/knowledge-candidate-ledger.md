# Knowledge Candidate Ledger — daw-header-libraries 2.135.0

**路径初判**: B（知识库扩展）— 存在已验证、可跨库复用的查重未命中候选
**task**: daw-header-libraries-2.135.0-r01-pc3-26-20260902T135624Z
**日期**: 2026-09-02

## 候选台账

### C1: OHOS clang15 前端在 C++20/23 + `-Weverything -pedantic-errors` 下对大型模板头文件段错误（ICE）

- **真实错误**: `clang-15: error: clang frontend command failed with exit code 139`，
  位于 `tests/daw_traits_test.cpp:759:71: current parser token ')'`；C++20 与 C++23
  两次独立构建均在同一文件同一 token 崩溃（可复现）。
- **根因**: OHOS SDK clang 15.0.4 前端解析大型模板头文件集合（本库 357 个头、测试编译
  携带 `-Weverything -pedantic-errors -pedantic -ftemplate-backtrace-limit=0`）时
  内部崩溃；属工具链前端缺陷，非本库代码错误（同一文件在默认 C++17 集编译通过）。
- **修复/规避**: 配方门禁保持默认 C++17（与 conan profile `cppstd=17` 一致）；
  C++20/23 上游扩展测试集在本工具链上不可达，记录为工具链限制而非库失败。
- **验证**: C++17 默认集 107/107 通过；C++20 构建 92 目标成功 + 1 文件 ICE 中断
  （93/123 ctest 通过，30 Not Run）；C++23 构建同上（92/127 通过，35 Not Run）。
- **适用范围**: 一切在 OHOS clang15 上以 -Weverything/-pedantic-errors 编译
  C++20/23 大型模板头库测试的适配任务。
- **查重结果**:
  - 正式知识（graph/E*.kv + doc/E*.md）: **未命中** — 检索 weverything/
    pedantic-errors/frontend command failed/internal compiler error 全库 0 命中。
  - 图谱（knowledge/doc/、index.tsv）: **未命中** — E040（mandb SIGSEGV 139）与
    E210（mimalloc MI_OVERRIDE 段错误）均为**运行时**崩溃；E222（FaultLogger）
    为崩溃调试方法论；E322/E307（header-only 配方/编译）为配方模式。均不同主题。
  - 草稿（knowledge/drafts/）: **未命中** — DRAFT-libcxx15-missing-cpp20-spaceship
    是**编译期**错误（缺 `<=>` 重载），非前端 ICE；主题不同。
  - 无覆盖 → 建立同 stem 草稿对 `DRAFT-daw-header-libraries-clang15-frontend-ice-cxx20-weverything.{kv,md}`。

### C2: header-only CMake INTERFACE 库配方模式（daw-header-libraries 实例）

- **真实错误**: 无（直接适配成功）。header-only INTERFACE 库配方要点：
  `package_type=header-library`、`cmake_file_name/cmake_target_name`、`cpp_info.libs=[]`、
  `CMAKE_SYSTEM_NAME=Linux` 注入（os in Linux/OHOS，R32）。
- **查重结果**: **已覆盖** — E257（header-only 无构建 G1）、E307（header-only
  编译 profile）、E321（nonstd-lite header-only Conan 2）、E322（INTERFACE 配方 +
  关闭默认 tests）、E470（header-library recipe）完整覆盖该模式。
- **结论**: 完整重复，复用既有知识，不建草稿。

## 路径决定

- C1 已验证、可跨库复用、四范围查重均未命中 → **满足路径 B 条件**
  （知识库扩展：问题/根因/方案/验证/适用边界/查重差异齐全）。
- C2 完整重复 → 路径 A 特征（常规基础适配），知识已存在于知识库。
- 判 **路径 B**：新增 1 个知识草稿（.kv/.md 同 stem 配对），PR 前缀改为
  【知识库扩展】（任务头规则：new_draft 且 .md/.kv 配对通过时）。
- 知识草稿与三方库归档文件（archives/d/daw-header-libraries/2.135.0/）进入同一 PR。