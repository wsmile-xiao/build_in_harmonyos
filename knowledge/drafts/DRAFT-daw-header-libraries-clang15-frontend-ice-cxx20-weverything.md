# DRAFT-daw-header-libraries-clang15-frontend-ice-cxx20-weverything：OHOS clang15 前端对大型模板头文件 ICE

> Contributor: pc3-26 | Status: Draft | Updated: 2026-09-02
> Source: daw-header-libraries 2.135.0 HarmonyOS PC adaptation（上游测试 C++20/23 扩展集）
> 对应：knowledge/drafts/DRAFT-daw-header-libraries-clang15-frontend-ice-cxx20-weverything.kv

## 现象

在 OHOS aarch64 环境（clang 15.0.4）用 `-DCMAKE_CXX_STANDARD=20` 或 `=23` 构建
daw-header-libraries 2.135.0 上游测试集时，clang 前端崩溃：

```text
clang-15: error: clang frontend command failed with exit code 139 (use -v to see invocation)
...
1.  tests/daw_traits_test.cpp:759:71: current parser token ')'
PLEASE ATTACH THE FOLLOWING FILES TO THE BUG REPORT:
Preprocessed source(s) and associated run script(s) ...
```

C++20 与 C++23 两次独立构建均在同一文件同一 token 崩溃（**可复现**）；默认
C++17 配置（与 conan profile `cppstd=17` 一致）则 107/107 测试全部通过。

## 与现有知识的关系（确认去重证据）

- 检索词：weverything / pedantic-errors / frontend command failed / internal
  compiler error / ICE / parser token / clang exit 139。
- 正式知识面（index.tsv + doc/）：0 命中。E040（mandb SIGSEGV 139）与 E210
  （mimalloc MI_OVERRIDE 段错误）均为**运行时**崩溃，E222（FaultLogger）为崩溃
  调试方法论，E322/E307 为 header-only 配方模式——均不同主题。
- 草稿面（knowledge/drafts/）：DRAFT-libcxx15-missing-cpp20-spaceship 是**编译期**
  `operator<=>` 缺失，非前端 ICE；主题不同。
- **无覆盖** → 建立本草稿对。

## 根因

OHOS SDK clang 15.0.4 前端解析大型模板头文件集合（本库 357 个头文件）且编译携带
`-Weverything -pedantic-errors -pedantic -ftemplate-backtrace-limit=0` 时内部
崩溃（segfault, exit 139）。属**工具链前端缺陷**（ICE），非本库代码错误——同一
文件在 C++17 集可编译通过。

## 方案（推荐）

1. 配方/门禁保持与 conan profile 一致的默认 C++17（`cppstd=17`），上游默认集
   完整通过（107/107）。
2. C++20/23 扩展测试集在本工具链不可达时，按**工具链前端限制**记录（含崩溃
   证据：命令/exit 139/崩溃文件行号 token/preprocessed 提示），计入测试台账
   分母但不计为库测试失败。
3. 不得通过删除/弱化测试集掩盖，不得把 ICE 当作库代码错误。

## 验证

```bash
# 复现（C++20/23 扩展集）
cmake -DDAW_ENABLE_TESTING=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang ..
cmake --build . -j8   # daw_traits_test.cpp:759 前端 139 崩溃

# 门禁（默认 C++17 集）
cmake --build . -j8 && ctest --test-dir build-test/tests -j8
# → 107/107 PASS (100%)
```

## 适用边界

- 适用：OHOS clang15 工具链下以 C++20/23 + 全量警告编译大型模板头库
  （header-only/泛型库）测试集的任务。
- 不适用：C++17 默认集构建、或工具链已升级 clang≥17 的环境。

## 查重差异

与 E040/E210（运行时段错误）、E222（崩溃调试）、DRAFT-libcxx15（编译期 <=> 缺失）
的区别：本条目聚焦**编译期前端 ICE**（frontend command failed + parser token +
exit 139），且给出"保持默认标准 + 工具链受限记录"的规避路径。