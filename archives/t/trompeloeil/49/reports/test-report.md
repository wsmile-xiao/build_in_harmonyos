# trompeloeil 49 测试报告

> **项目**: trompeloeil 49（header-only C++ mocking framework）
> **测试日期**: 2026-09-16
> **测试环境**: HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64）/ OHOS SDK clang 15.0.4 / libc++ 15 / Conan 2.29.1
> **测试类型**: 上游官方测试套件（Catch2 v3 自测 + 68 个 expect-to-fail 编译用例）+ 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游运行时用例（C++14 self_test） | 604（1361 断言） | 100% PASS |
| 上游运行时用例（C++20 self_test，含协程） | 615（1394 断言） | 100% PASS |
| thread_terror / custom_recursive_mutex | 2/2 | 100% PASS |
| 负向编译用例 C++14（上游规则排除 18） | 50/50 | 100% PASS |
| 负向编译用例 C++20 | 68/68 | 100% PASS |
| 消费者测试（test_package） | 4（5 断言） | 100% PASS |
| **失败/跳过（非上游规则排除）** | **0** | **0%** |

**核心功能通过率**: **100%**（118 个负向编译用例执行批次中 0 FAIL；1219 个运行时用例 0 FAIL）

---

## 二、测试结论

### 2.1 总体评价

**PASS** — 上游测试套件在 OHOS aarch64（clang 15.0.4 / libc++ 15）上**零补丁、零用例修改**全部通过；C++20 协程 mock 用例同样通过；68 个负向编译用例诊断文本零漂移。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 构建期联网下载 Catch2（上游 CMake 兜底行为） | 构建可复现性 | 🟡 已通过配方预置 Catch2 v3 消除 |
| 负向测试驱动器依赖 GNU parallel | OHOS 无该命令 | 🟢 已用线程池驱动同一脚本替代 |

### 2.3 可用功能清单

```
✅ 期望声明：REQUIRE_CALL / ALLOW_CALL / FORBID_CALL（604/615 用例覆盖）
✅ 参数匹配器：_ / gt / re / any / duck-typed 等（自测覆盖）
✅ 基数与序列：TIMES / IN_SEQUENCE / 生命周期（自测覆盖）
✅ 副作用与返回值：LR_SIDE_EFFECT / RETURN / THROW（自测覆盖）
✅ 违反期望报告：expectation_violation（消费者测试用例 4 实测）
✅ C++20 协程：CO_RETURN / CO_YIELD / CO_THROW（C++20 self_test 615 用例覆盖）
✅ 负向编译断言：68 个 expect-to-fail 翻译单元全部按预期失败
```

### 2.4 已知限制

1. 上游 `compilation_errors` 在 C++14 下按上游自带 `// exception:` 规则排除 18 个（协程等）用例；C++20 下全部 68 个执行。
2. 上游自测编译体量大（约 10 分钟含两个标准与负向套件），CI 需预留构建时长。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `self_test`（C++14） | 期望/匹配器/序列/报告 全量 | ✅ 1361 assertions in 604 test cases |
| `self_test`（C++20） | 追加协程 mock 用例（`test_co_mock.cpp`） | ✅ 1394 assertions in 615 test cases |
| `thread_terror` | 多线程调用/返回计数 | ✅ exit 0（计数对称） |
| `custom_recursive_mutex` | 自定义递归互斥量适配 | ✅ exit 0（`Pass!`） |
| `compilation_errors`（C++14，50 生效） | expect-to-fail + 诊断正则匹配 | ✅ 50 PASS / 0 FAIL |
| `compilation_errors`（C++20，68 全量） | expect-to-fail + 诊断正则匹配 | ✅ 68 PASS / 0 FAIL |
| `test_package/test_trompeloeil` | 消费者：RETURN/匹配器/副作用/违反报告 | ✅ 5 assertions in 4 test cases |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无（上游 `// exception:` 规则排除的 18 个 C++14 负向用例属上游规则行为，非本次跳过） | — |

---

## 四、关键问题分析

### 问题1: 上游 CMake 找不到 Catch2 时构建期下载 catch.hpp

**现象**：首次在设备上直接 `cmake` 配置上游源码时，`build/test/catch/catch2/catch.hpp` 被创建（657,891 字节，来自 `https://github.com/catchorg/Catch2/releases/download/v2.13.7/catch.hpp`）。

**根因分析**：`test/CMakeLists.txt` 的 `find_package(Catch2 3 QUIET)` 与 `find_package(Catch2 2...<3 QUIET)` 都失败后，无条件走 `file(DOWNLOAD ...)` 兜底。CI 环境若网络不可达或禁止外网，将直接配置失败；即便可达也违反“构建期不联网”约束（且混入 Catch2 v2 单头，与声明矩阵不符）。

**解决方案**：配方 `build_requirements()` 增加 `tool_requires("catch2/3.8.1")`，`build()` 中把
`self.dependencies.build["catch2"].package_folder` 传给 `-DCMAKE_PREFIX_PATH`。实测：不再产生下载文件，
编译定义含 `-DCATCH2_MAIN -DCATCH2_VERSION=3`。

### 问题2: GNU parallel 缺失导致负向测试无法驱动

**现象**：`check_errors.sh` 第 34 行 `parallel ../verify_compilation_error.sh ::: $files`，OHOS 无 `parallel`（toybox 提供 `xargs`/`nproc`，无 `parallel`）。

**根因分析**：上游 CI 使用 Ubuntu/GitHub Actions（`brew install parallel`/系统包）。OHOS 上即使用 `xargs -P` 替换，也存在两处边界：`mktemp` 默认在只读的 `/tmp`；`continue` 在不同 shell 中的退出码差异（上游脚本对退出码不敏感，按输出行计数）。

**解决方案**：`build()` 内以 `ThreadPoolExecutor(2)` 逐用例执行**未修改的** `verify_compilation_error.sh`：
- `CXX` 取自 `tools.build:compiler_executables`（绝对路径）；
- `TMPDIR` 指向 `${build_folder}/negative-tests-tmp`；
- 与上游等价地按输出行含 `PASS`/`FAIL` 计数，任一 `FAIL` 即 `conan create` 失败。

### 问题3: OHOS `/tmp` 只读

**现象**：`mktemp` 若落到 `/tmp` 报 Read-only（E002）。

**根因分析**：OHOS 系统 `/tmp` 只读，须显式 TMPDIR。

**解决方案**：同上，在负向测试子进程环境中固定 `TMPDIR`。

---

## 五、测试环境

```
uname -a: HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP aarch64
clang version 15.0.4 (OHOS SDK LLVM, /srv/workspace/llvm-release/2026_0313_llvm15_release)
cmake 4.4.3 / GNU Make 4.4.1 / Conan 2.29.1 (OHOS 适配版)
conan profile: os=OHOS 6.0, arch=armv8, clang 15, libc++, cppstd=17, build_type=Release
依赖: catch2/3.8.1（tool_requires，仅用于构建期上游自测与消费者测试）
```

---

*报告生成时间: 2026-09-16*
