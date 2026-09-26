# 测试报告 — cassiopee-c 1.0.9

> **项目**: cassiopee-c  
> **测试日期**: 2026-09-25  
> **测试环境**: HarmonyOS PC (OHOS 6.0) aarch64，clang 15.0.4，OHOS SDK 26.0.0.18，conan 2.29.1  
> **测试类型**: 官方测试套件 + 手动功能测试（上游 + 鸿蒙专项 + 消费者）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游用例总数（源码声明） | 14 | 100% |
| 通过 (PASS) | 14 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过/未运行 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（14/14，含 13 个 cppunit TC + 1 个 test.py CLI 用例）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游测试全量运行通过，鸿蒙专项测试 3/3 通过，消费者用例在 conan create 中真实编译链接运行通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| boost CMakeDeps include 目录为空（1.90.0.3 版） | 消费者编译 Cassiopee.h（公开头含 boost 头）失败 | 🟡（已解决：改用 1.90.0.4.1） |
| 测试二进制相对 DT_NEEDED（`../lib/libcassie.so`） | ctest 运行时加载失败 | 🟢（运行时环境注入解决，非代码缺陷） |
| 上游 test.py 假设二进制在源码根 `bin/` | 脚本直接运行失败 | 🟢（符号链接满足路径假设，未改上游脚本） |

### 2.3 可用功能清单

```
✅ 后缀树索引构建（CassieIndexer::index，支持 reduction 还原）
✅ 精确/替换/插入缺失搜索（CassieSearch::search，DNA/RNA/Protein 模式）
✅ 多义碱基与 N 匹配（ambiguity / nmax / max_subst / max_indel）
✅ 索引序列化保存/加载（boost serialization：.cass.idx/.cass.meta）
✅ CLI 工具 cassiopee（索引/搜索）与 cassiopeeknife（FASTA 转换）
✅ 公开头文件 Cassiopee.h + tree.hh 安装，消费者可编译链接
```

### 2.4 已知限制

1. 上游测试二进制与 CLI 的 DT_NEEDED 为相对路径 `../lib/libcassie.so`，运行需在源码根 `lib/` 建立符号链接（或由安装布局满足）；已在 test_package/消费者路径验证可正常运行。
2. test.py 需在源码根存在 `bin/` 目录（符号链接至 build/bin）时按上游路径直接运行。

---

## 三、测试详情

### 3.1 通过的测试（上游 14 用例）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| testIndex | 前缀树索引构建 | ✅ PASS |
| testIndexWithReduction | 还原模式下索引 | ✅ PASS |
| testSearchInReduction | 还原模式搜索 | ✅ PASS |
| testAmbiguity | 多义搜索 | ✅ PASS |
| testSearchWithError | 允许替换错误搜索 | ✅ PASS |
| testSearchAfterN | N 之后搜索 | ✅ PASS |
| testSearchWithN | 含 N 匹配 | ✅ PASS |
| testReducedSearchAfterN | 还原模式 + N 后搜索 | ✅ PASS |
| testReducedSearchWithN | 还原模式 + N 匹配 | ✅ PASS |
| testProtein | 蛋白模式搜索 | ✅ PASS |
| testLoadSave | 索引保存/加载 | ✅ PASS |
| testMultiIndex | 多索引 | ✅ PASS |
| testSearchWithMorphism | 形态映射搜索 | ✅ PASS |
| test.py（CLI） | 全子串/全位置穷举搜索 + 输出比对 | ✅ PASS（exit 0，无 Not found） |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| （无） | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| （无） | — |

### 3.4 鸿蒙专项测试（tests/harmonyos_test.cxx，3 用例）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| case1 序列化往返 | save() → 重建 index() 自动 load | ✅ PASS |
| case2 还原模式搜索 | reduction 搜索命中 6 位置 | ✅ PASS |
| case3 公开 API 可用性 | 安装产物 libcassie.so 编译链接运行 | ✅ PASS |

### 3.5 消费者验证（test_package/consumer_test.cxx）

在 `conan create`（G2）中真实编译、链接、运行消费者二进制并通过：
索引构建 → 搜索（matches 列表）→ 序列化保存 → 重建加载（index_loaded_from_file）→ 退出码 0。

---

## 四、关键问题分析

### 问题1: boost/1.90.0.3 CMakeDeps include 目录为空

**现象**：conan-verify G2 test_package 编译 `Cassiopee.h:10: fatal error: 'boost/archive/text_oarchive.hpp' file not found`；检查生成器 `boost_INCLUDE_DIRS_RELEASE` 为空。

**根因**：制品仓 boost/1.90.0.3 包生成的 CMakeDeps 未导出 include 目录，而 cassiopee-c 公开头 Cassiopee.h 直接包含 boost/archive 头文件，消费者编译时必须可见 boost 头。

**解决方案**：依赖改用 boost/1.90.0.4.1（CMakeDeps 正确导出 `${boost_PACKAGE_FOLDER_RELEASE}/include`，且含 libboost_serialization.so/libboost_iostreams.so）；test_package 显式 requires boost（adql 同款先例）。G2 通过。

### 问题2: 测试二进制动态加载相对路径

**现象**：ctest 报 `Error relocating ... _ZN13CassieIndexerD1Ev: symbol not found`。

**根因**：NDT_NEEDED 为相对路径 `../lib/libcassie.so`（CMake 构建布局），从源码根运行无法解析。

**解决方案**：源码根 `lib/` 建立符号链接 → build/lib/libcassie.so + LD_LIBRARY_PATH 注入 boost/glog/gflags/cppunit 库目录。属运行时环境恢复，未修改上游代码。

---

## 五、测试环境

```
cassiopee-c 1.0.9 (github.com/osallou/cassiopee-c tag 1.0.9)
字节序/架构: arm64 (aarch64-unknown-linux-ohos)
编译器: clang 15.0.4 (OHOS SDK 26.0.0.18 llvm)
Conan 2.29.1 (OHOS 适配版), profile ci/conan/profiles/ohos-aarch64
构建: CMake (补丁提升 cmake_minimum_required 3.5)
依赖: boost/1.90.0.4.1, glog/0.7.1, cppunit/1.15.1
```

*报告生成时间: 2026-09-25*