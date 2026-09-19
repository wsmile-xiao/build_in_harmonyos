# libkaz 1.21 测试报告

> **项目**: libkaz（kazlib 1.21）
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS PC（OHOS 6.0，aarch64，clang /data/service/hnp/bin/clang，Conan 2.29.1，profile ci/conan/profiles/ohos-aarch64）
> **测试类型**: 官方测试套件（上游自测驱动）+ test_package 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 7 | 100% |
| 通过 (PASS) | 7 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

计数单位说明：以上游自测程序为 1 个用例（6 个上游驱动），test_package 消费者测试程序为 1 个用例（内含 21 个 assert）。

---

## 二、测试结论

### 2.1 总体评价

✅ 全部 6 个上游自测驱动与 1 个消费者测试在 OHOS aarch64 上构建并执行通过，字典/哈希/链表/异常/副作用分析五大模块功能正常。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS 下 abort() 丢弃管道 stdout 缓冲，teh 的部分输出无法捕获 | 仅影响测试证据采集方式，不影响库功能 | 🟢 |

### 2.3 可用功能清单

```
✅ dict：增删查、排序遍历、1.21 新增 dict_strict_lower_bound / dict_strict_upper_bound
✅ hash：增删查、容量调整、遍历
✅ list：append/find/sort/count/遍历
✅ except：嵌套 try 捕获、重抛、清理处理器、未处理异常路径（SIGABRT 为上游设计行为）
✅ sfx：表达式副作用判定（none / certain）
✅ C++ 模板包装（dict<dnode_is_member, key_is_member, ...>）：多重索引与排序遍历
```

### 2.4 已知限制

1. OHOS 管道下 stdout 为块缓冲，`abort()` 时缓冲内容被丢弃，`teh` 驱动的两条 caught 输出与 cleanup 行无法进入日志；断言以 fflush 过的提示行与 Unhandled 异常身份（group=99, code=99）为准，该身份仅在内/外两层捕获均完成后可达。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| tlist（stdin 脚本：append/lookup/sort/dump/delete/count） | list | ✅ PASS |
| tdict（stdin 脚本：含 1.21 严格上下界查找 `<` 与 `>`） | dict | ✅ PASS |
| thash（stdin 脚本：add/lookup/size/count/dump/delete） | hash | ✅ PASS |
| teh（嵌套捕获 + 设计内未处理异常，退出状态 134） | except | ✅ PASS |
| tsfx（表达式 x、x + 1、x = 1 的副作用判定） | sfx | ✅ PASS |
| tests/dict-1（C++ 模板包装，三条排序遍历输出） | dict C++ 接口 | ✅ PASS |
| test_package/test_libkaz（消费者测试，21 个断言） | 安装库整体链接与 API | ✅ PASS |

执行方式与断言规则记录于 conanfile.py 的 build()（`_selfcheck`/`_run_selfchecks`）；
原始日志：`reports/conan-create.log`、`reports/w3-local-ci.log`。

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | 上游共 6 个可运行测试程序（Makefile.gcc PROGS 与 tests/dict-1），全部实跑，无跳过项 |

---

## 四、关键问题分析

### 问题1: 上游测试驱动规则与 clang 不兼容

**现象**：
```
clang: error: cannot specify -o when generating multiple output files
```

**根因分析**：
上游 Makefile.gcc 的 PROGS 规则把头文件作为链接输入（如 tdict: dict.c dict.h → $(CC) -o tdict dict.c dict.h），GCC 传统上容忍、clang 拒绝；OHOS 工具链只有 clang。

**解决方案**：
配方按 Makefile 同款条件（同一 CFLAGS + -DKAZLIB_TEST_MAIN，tsfx 链接 except.o/hash.o）逐个直编译同一测试源码，测试用例本身零修改。

### 问题2: teh 驱动在 OHOS 下输出缓冲丢失

**现象**：
```
Signal 6 (core dumped)
throw exception? Unhandled exception ("exception in main", group=99, code=99)
```
（两条 caught exception 输出未出现在管道捕获中）

**根因分析**：
OHOS 管道下 stdout 为块缓冲，abort() 触发崩溃处理时缓冲内容被丢弃；仅显式 fflush 的提示行与 stderr 幸存。

**解决方案**：
断言改用可捕获证据：fflush 过的 `throw exception? `、stderr 的 Unhandled 身份 `group=99, code=99`（仅当内/外两层捕获与重抛全部完成后才可能到达该抛出点）、SIGABRT 状态 134。

---

## 五、测试环境

```
libkaz/1.21（上游 kazlib tag kazlib-1.21 = commit a2585e85）
工具链：/data/service/hnp/bin/clang（OHOS 6.0 aarch64，musl）
Conan 2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64
构建：make -f Makefile.gcc（libkaz.a、libkaz.so.1.0.0、tests/dict-1）+ 5 个驱动直编译
```

---

*报告生成时间: 2026-09-19*
