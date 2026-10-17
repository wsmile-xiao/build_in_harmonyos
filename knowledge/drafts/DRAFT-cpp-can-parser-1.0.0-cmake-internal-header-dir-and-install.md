# DRAFT-cpp-can-parser-1.0.0-cmake-internal-header-dir-and-install：上游 CMakeLists 缺内部头目录 + install 规则损坏

> Contributor: AtomCode (pc2-2) | Status: Draft | Updated: 2026-09-05
> Source: cpp-can-parser 1.0.0 HarmonyOS PC adaptation（R01，patch 0001-CMakeLists.txt.patch）
> 对应：knowledge/drafts/DRAFT-cpp-can-parser-1.0.0-cmake-internal-header-dir-and-install.kv

## 现象

官方 tag v1.0.0 的仓库在干净 CMake 配置下**库自身无法编译**：

```text
src/models/CANDatabase.cpp:1:10: fatal error: 'CANDatabase.h' file not found
src/parsing/ParsingUtils.h:8:10: fatal error: 'CANDatabase.h' file not found  # 经 DBCParser.h 链入
```

同时 install 规则 `install(FILES cpp-can-parser ${CMAKE_CURRENT_BINARY_DIR}/cpp_can_parser_export.h
DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/include)` 把 target 名当文件路径引用（源目录无此文件）、
且装入二进制 build 目录而非标准 prefix，产物不可消费。

## 根因

- 头文件布局：公共头在 `include/cpp-can-parser/CANDatabase.h`（对外用法
  `#include <cpp-can-parser/CANDatabase.h>`），而内部源码 `src/**/*.cpp`、
  `tests/test-parsing.cpp` 一律用短名 `#include "CANDatabase.h"`。
  上游 `target_include_directories` 只加了 PUBLIC `include/` 与 PRIVATE `src/parsing`，
  **独缺 `include/cpp-can-parser` 这一级**，于是库自身所有目标编译时找不到头。
- install 规则：`install(FILES cpp-can-parser ...)` 引用的是 target 名（不是文件），
  且 `DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/include` 目标是构建目录而非安装 prefix。
- export 头：`generate_export_header` 生成的 `cpp_can_parser_export.h` 未安装进公共头目录
  （公共头以 `#include "cpp_can_parser_export.h"` 引用，需与头文件同目录安装）。

## 验证（真实证据）

- 修复前：cmake --build 在库目标即 fatal error（compile_adaptation.log 前段）；
  cpc-test-parsing 同样因缺 include 路径失败
- 修复后（补 PRIVATE include 目录 + install(TARGETS)+头文件+export 头重写）：
  cmake --build rc=0；上游 cpc-test-parsing "Success. All tests passed." rc=0；
  conan create rc=0；安装产物核验
  `$PREFIX/lib/libcpp-can-parser*` 与 `$PREFIX/include/cpp-can-parser/{CANDatabase.h,
  CANDatabaseAnalysis.h,cpp_can_parser_export.h}` 齐全（日志 compile_adaptation.log、
  ctest_full.log、conan_create.log）

## 适用边界

- 触发面：上游 CMake 工程把公共头放 `include/<subdir>`、内部源却用短名 include
  （缺 PRIVATE 目录导致库自身编译失败）；`install(FILES <target>)` 误用或安装到
  二进制目录；`generate_export_header` 产物未随头文件安装
- 与 E217 的差异（查重关键）：E217 根因是**配方 package_info includedirs 配置**
  与上游头装到子目录的错配（test_package 阶段 `fatal error: x.h file not found`）；
  本条目根因是**上游 CMakeLists 自身缺 include 目录**（库编译阶段即失败）与
  **install 目标引用损坏**，修复在上游源码补丁（refresh-patch），非配方配置
- 反例：仅消费者 include 路径问题的场景（上游 CMake 正常、配方 includedirs 错）
  应套用 E217 方案而非本条目
- 推广价值：可跨库复用——诊断三步（看头文件布局 → 看 target_include_directories →
  看 install 规则）+ 补丁式修复 + 安装产物核验

## 查重

四范围（正式 knowledge/graph/*.kv、index.tsv、knowledge/drafts/、graph engine）：
E217（airspyhf）为 trigger_overlap/solution 部分的既有条目（头在 include/<subdir> 场景
一致，但根因位置与修复方案不同）；engine 对错误签名未返回直接命中（仅 E169/E291 无关
条目）。七轴查重详见 archives/c/cpp-can-parser/1.0.0/reports/knowledge_candidate_ledger.md
（候选 B，similar_to E217）。