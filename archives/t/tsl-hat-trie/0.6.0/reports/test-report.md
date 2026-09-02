# tsl-hat-trie 0.6.0 测试报告

> **项目**: tsl-hat-trie 0.6.0（header-only HAT-trie 实现）
> **测试日期**: 2026-09-01
> **测试环境**: HarmonyOS PC aarch64（os=OHOS, arch=armv8, clang 15.0.4, libc++, c++17）
> **测试类型**: 上游官方测试套件（Boost.Test）+ HarmonyOS 专项消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件 | 2 套（test_htrie_map + test_htrie_set） | 100% |
| 上游测试结果 | No errors detected | 100% |
| OHOS 专项测试断言 | 13 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 官方上游测试套件完整运行无错误，HarmonyOS 专项消费者测试 13 项断言全部 PASS。

### 2.2 主要问题

无。

### 2.3 可用功能清单

```
✅ htrie_map: insert / at / count / find
✅ htrie_map: equal_prefix_range 前缀搜索
✅ htrie_map: longest_prefix 最长匹配前缀
✅ htrie_map: erase_prefix 前缀删除
✅ htrie_map: serialize / deserialize 序列化往返
✅ htrie_set: insert / count
```

### 2.4 已知限制

1. 上游测试需要 Boost.Test 库，本环境用 ohpcd 制品仓 boost/1.90.0 的 `libboost_unit_test_framework.a` 静态链接运行。
2. 本库为 header-only，无构建期产物（bin/lib 为空），L2/L4/L5 类产物门禁不适用。

---

## 三、测试详情

### 3.1 通过的测试（上游官方套件）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_htrie_map 套件 | htrie_map 全量上游用例（trie_map_tests.cpp，含模板实例化多组） | ✅ PASS |
| test_htrie_set 套件 | htrie_set 全量上游用例（trie_set_tests.cpp，含模板实例化多组） | ✅ PASS |

运行命令：
```
clang++ -std=c++11 -O2 -DTSL_DEBUG -stdlib=libc++ \
  -I include -I <boost>/include \
  main.cpp trie_map_tests.cpp trie_set_tests.cpp \
  <boost>/lib/libboost_unit_test_framework.a -o tsl_hat_trie_tests
./tsl_hat_trie_tests --log_level=test_suite
```
输出结尾：`Leaving test module "hat_trie_tests"; testing time: 355989us` + `*** No errors detected`

### 3.2 通过的测试（HarmonyOS 专项消费者测试，reports/ohos_special_test.cpp）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| htrie_map size/at/count | 插入与精确查找 | ✅ PASS |
| equal_prefix_range("open") | 前缀搜索命中 2 项 | ✅ PASS |
| longest_prefix | 最长前缀命中 | ✅ PASS |
| erase_prefix | 前缀删除 2 项 | ✅ PASS |
| htrie_set count | 集合查找 | ✅ PASS |
| serialize/deserialize | 序列化往返一致 | ✅ PASS |

运行命令：
```
/data/service/hnp/bin/clang++ -std=c++17 -O2 -stdlib=libc++ \
  -I <src>/include reports/ohos_special_test.cpp -o ohos_special_test
./ohos_special_test
```
退出码 0，13 项断言全部 PASS，输出 `OHOS special test OK: tsl-hat-trie 0.6.0 consumer API verified on OHOS aarch64`。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（上游套件与专项测试均完整运行）。

---

## 四、关键问题分析

### 问题1: 上游测试链接时 main 重复定义

**现象**：`ld.lld: error: duplicate symbol: main`（main.cpp 与 libboost_unit_test_framework.a 的 unit_test_main.o 均定义 main）

**根因分析**：main.cpp 定义了 `BOOST_TEST_MODULE`/`BOOST_TEST_DYN_LINK`，header-only 场景静态链接 Boost.Test 时头部内联 main 与库内 main 冲突。

**解决方案**：编译 main.cpp 时加 `-DBOOST_TEST_NO_MAIN`，由 Boost 静态库提供 main。

---

## 五、测试环境

```
OS: HarmonyOS PC aarch64
Compiler: clang 15.0.4 (libc++, -stdlib=libc++)
Conan: 2.29.1 (OHOS 适配版)
Boost.Test: 1.90.0 (ohpcd 制品仓)
C++ 标准: c++11 (上游) / c++17 (OHOS 专项)
```

---

*报告生成时间: 2026-09-01*
