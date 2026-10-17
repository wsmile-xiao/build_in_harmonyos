# DRAFT-cassiopee-c-glog-string-order-and-cmakedeps-consumer-include：glog <string> 前置包含 + CMakeDeps 传递依赖 include 的消费者侧显式声明

> Contributor: pc1-43 | Status: Draft | Updated: 2026-09-25
> Source: cassiopee-c 1.0.9 HarmonyOS PC adaptation（patches/0002-0003 + test_package 显式 requires boost/1.90.0.4.1）
> 对应：knowledge/drafts/DRAFT-cassiopee-c-glog-string-order-and-cmakedeps-consumer-include.kv

## 现象一：glog 0.7.x flags.h 的 DECLARE_string 宏在 C++17 下报 fLS 命名空间错误

源码在包含 `<glog/logging.h>` 前未包含 `<string>`，编译报：

```text
glog/flags.h:112:1: error: cannot define or redeclare 'string' here because namespace 'fLS' does not enclose namespace 'std'
    DECLARE_string(log_backtrace_at);
glog/flags.h:100:29: note: expanded from macro 'DECLARE_string'
    extern GLOG_EXPORT std::string& FLAGS_##name;
```

直链场景（上游 CMakeLists 用裸目标名 `glog` 链接、未 find_package）下还会先报
`unknown type name 'GLOG_EXPORT'`（glog 0.7.x 消费宏 `GLOG_USE_GLOG_EXPORT` 缺失）。

**根因**：glog 0.7.x `glog/flags.h` 的 `DECLARE_string(name)` 宏展开
`extern GLOG_EXPORT std::string& FLAGS_name;`，依赖 `<string>` 已先行包含
（libc++ C++17 下不自动前置），且 `GLOG_USE_GLOG_EXPORT` 定义必须在包含前注入。

**修复**（cassiopee-c 实测，退出码 0）：
1. 源码补丁：在 `<glog/logging.h>` 之前加 `#include <string>`（patches/0002-0003）；
2. 配方 `generate()` 注入 `-DGLOG_USE_GLOG_EXPORT` 与依赖 include/lib 路径
   （上游裸目标链接场景）；走 CMakeDeps 目标时 `glog::glog` 已自带该宏。

## 现象二：公开头含 boost 头的库，test_package 消费者编译报 boost 头 not found

```text
Cassiopee.h:10:10: fatal error: 'boost/archive/text_oarchive.hpp' file not found
```

**根因**：cassiopee-c 公开头 `Cassiopee.h` 直接包含 `<boost/archive/*.hpp>`。
制品仓 boost/1.90.0.3 的 CMakeDeps 组件（Boost::headers 等）
`INTERFACE_INCLUDE_DIRECTORIES` 为空——include 目录只出现在 CMakeToolchain 的
`CMAKE_INCLUDE_PATH`（仅 find_path 搜索用，不会自动变成编译 `-I`）。test_package
仅 `requires(cassie)` 时 boost 是传递依赖，其 include 元数据为空导致消费者编译失败。

**修复**（cassiopee-c 实测，G2 conan create 退出码 0）：
1. 依赖优先选 CMakeDeps 正确导出 include 目录的版本：boost/1.90.0.4.1 生成
   `boost_INCLUDE_DIRS_RELEASE = "${boost_PACKAGE_FOLDER_RELEASE}/include"`，
   boost/1.90.0.3 为空的同类坑；
2. test_package `requirements()` 显式 `self.requires("boost/<版本>")`
   （adql 2.0 同款先例）——公开头依赖 boost 的库，消费者必须显式声明该传递依赖。

## 验证（真实日志，SHA-256 见归档 notes.md）

- 本地 make 全量编译 rc=0；conan-verify G2 conan create rc=0（test_package 消费者
  consumer_test.cxx 编译链接运行通过）；
- 上游 14 用例全过（13 cppunit + test.py）；鸿蒙专项 3 用例全过。

## 适用边界 / 反例

- 适用：C++17 下直接包含 `<glog/logging.h>` 且其后才用标准容器的老库；
  公开头直接包含 boost 头文件、消费者在 Conan 2 + CMakeDeps 下编译的库。
- 反例：glog 头文件已自带 `<string>` 前置的新版、boost 作为直接依赖（非传递）
  且 CMakeDeps include 正确导出时，不需要显式 requires 补救。

## 与现有知识的关系

- `similar_to`：E498（headerless include 清空，方向相反）、E221（CMakeDeps 公开契约）、
  E103/DRAFT-E321（cmake4 策略族，不同根因）
- `caused_by`：glog 0.7.x flags.h 宏设计 + C++17 libc++；boost 包 CMakeDeps include 导出缺失
- `prerequisite_of`：无 | `conflicts_with`：无
- 四范围查重：index.tsv/doc/graph/drafts 均未命中本组合（glog fLS + CMakeDeps 传递 include 消费者补救）

## 查重差异（knowledge-candidate-ledger 七轴摘要）

| 轴 | 现象一（glog） | 现象二（CMakeDeps 传递 include） |
|---|---|---|
| exact_duplicate | false | false |
| causal_duplicate | false | false |
| trigger_overlap | false | true（INTERFACE_INCLUDE_DIRECTORIES 域） |
| solution_overlap | false | partial（与 E498 方向相反） |
| combination_novelty | true | true |
| boundary_novelty | true | true |
| test_migration_novelty | false | false |
