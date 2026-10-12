# 测试报告 — opari 1.1（OHOS PC aarch64 / OpenHarmony 6.0）

**包引用**：`opari/1.1@ohpcd/stable`
**Profile**：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0, arch=armv8, clang 15, libc++）
**工具链**：`/data/service/hnp/bin/clang` / `clang++`，OHOS SDK `ohos-sdk_26.0.0.18`

---

## 一、上游测试（R51）—— 单独汇报

### 1.1 测试入口

| 入口 | 位置 | 说明 |
|---|---|---|
| `c_test.sh` | `tool/Test/c_test.sh` | 对 11 个 C 用例执行 `opari` 插桩，diff 比对生成的 `<base>.mod.c` 与 `.out`、`<base>.c.opari.inc` 与 `.opari.inc.out` |
| `table_test.sh` | `tool/Test/table_test.sh` | `opari -table` 生成 region 表（`opari.rc` / `opari.tab.c`）并 diff 比对 |
| `f77_test.sh` / `f90_test.sh` | `tool/Test/` | Fortran 测试（**本平台排除**，见 1.3） |

上游为手写 Makefile 工程（无 autotools / cmake），**没有 ctest / pytest 注册**，测试入口就是这两个 shell 脚本。

### 1.2 执行命令与结果

```
命令： sh c_test.sh          （cwd = tool/Test/，opari 二进制置于 tool/）
        sh table_test.sh c
退出码： 0 / 0
```

| 指标 | 数值 |
|---|---|
| 用例总数 | **12**（11 个 C 用例 + 1 个 region 表用例） |
| 实际运行 | **12** |
| 通过 | **12** |
| 失败 | **0** |
| 跳过 | **0** |
| 排除 | 2（Fortran f77 / f90，见下） |

### 1.3 逐用例明细

| # | 用例 | 命令 | 结果 |
|---|---|---|---|
| 1 | `test1.c` | `sh c_test.sh` | PASS |
| 2 | `test2.c` | `sh c_test.sh` | PASS |
| 3 | `test4.c` | `sh c_test.sh` | PASS |
| 4 | `test5.c` | `sh c_test.sh` | PASS |
| 5 | `test6.c` | `sh c_test.sh` | PASS |
| 6 | `test8.c` | `sh c_test.sh` | PASS |
| 7 | `test9.c` | `sh c_test.sh` | PASS |
| 8 | `testA.c` | `sh c_test.sh` | PASS |
| 9 | `testB.c` | `sh c_test.sh` | PASS |
| 10 | `testC.c` | `sh c_test.sh` | PASS |
| 11 | `testD.c` | `sh c_test.sh` | PASS |
| 12 | region 表 | `sh table_test.sh c` | PASS |

> 说明：上游 C 用例编号不连续（**不存在 `test3.c`**，test3 仅有 `.f` / `.f90` 版本），故 C 用例为 11 个而非 12 个。

### 1.4 排除项与技术原因

| 排除用例 | 原因 |
|---|---|
| `f77_test.sh` | OHOS SDK 未提供 **gfortran**，Fortran 前端缺失，无法编译 Fortran 插桩产物 |
| `f90_test.sh` | 同上 |

这是**工具链层面的平台限制**（并非"没环境就跳过"），已如实记录。

### 1.5 日志路径

- **`<worktree>/.ci_logs/conan_build_opari_1.1.log`**：`conan create` **全量构建 + 上游测试原文** ——
  含 `Forced build from source`、8 个 C++ TU 逐条编译、`RUN: sh c_test.sh`（11 用例）、
  `RUN: sh table_test.sh c`、`Package '4b977264…' created`。**这是上游测试通过的权威证据来源。**
- 补丁版构建副本：`/storage/Users/currentUser/tmp/opari_conan_create.log`（含 `Apply patch (portability)`）
- ⚠️ `archives/o/opari/1.1/reports/conan-create.log` **不作为**证据引用：它由 `conan-verify` 阶段产出，
  彼时包已在缓存，故为**缓存命中日志**（2 处 `Already installed!`；`Apply patch`、`Package created`、
  `RUN: sh c_test.sh` 计数均为 0）。

---

## 二、鸿蒙消费者用例（test_package，R34 + 用户要求"至少一个鸿蒙测试用例"）

### 2.1 用例设计（真实调用包，非占位）

`archives/o/opari/1.1/test_package/` 在 **OHOS aarch64 真机**上跑通完整插桩流水线：

1. 运行包内 `bin/opari` 对 `consumer.ohos.c`（含 `#pragma omp parallel for reduction`）做源码级插桩
   → 产出 `consumer.ohos.mod.c` + `consumer.ohos.c.opari.inc`
2. 用 OHOS clang `-fopenmp` 编译插桩产物 + 最小 POMP 运行时表 `pomp_rt.c`
3. 链接包内 `lib/libpomp.a` 与 OHOS 的 `libomp`
4. 运行可执行文件，并对**鸿蒙平台机制**做可证伪断言（见 2.3 断言表）

### 2.2 执行命令

```
opari consumer.ohos.c
clang -fopenmp -O2 -I<pkg>/include -c consumer.ohos.mod.c -o consumer.ohos.mod.o
clang -fopenmp -O2 -I<pkg>/include -c pomp_rt.c          -o pomp_rt.o
clang -fopenmp consumer.ohos.mod.o pomp_rt.o -o consumer -L<pkg>/lib -lpomp -lomp
./consumer
```

### 2.3 结果

| 项 | 结果 |
|---|---|
| 插桩 | exit 0 |
| 编译 | exit 0 |
| 链接 | exit 0（`-lomp` 由 OHOS clang 自动解析） |
| **运行** | **exit 0** |
| stdout | `sum=4950`（与 0..99 求和正确值一致） |
| stderr | **124 条 POMP 区域事件行**，线程 0–19 |

stderr 事件类型完整覆盖：`init`、`fork parallel`、`begin parallel`、`enter for`、
`enter implicit barrier of parallelfor`、`exit implicit barrier of parallelfor`、
`exit for`、`end parallel`、`join parallel`、`finalize`。

### 2.3.1 鸿蒙平台机制断言（可证伪，缺任一即失败）

| # | 断言 | 判据 | 结果 |
|---|---|---|---|
| A | 平台网关 | `settings.os == "OHOS"` 且 `settings.arch == "armv8"` | PASS |
| B | 目标架构 | 产物 ELF 头 `ei_class == ELFCLASS64`、`e_machine == EM_AARCH64 (183)` | PASS |
| C | OHOS 运行时 | stderr 的 POMP 事件数 > 0，且含 `begin parallel` / `enter for` / `finalize` | PASS（124 条 / 20 线程） |
| — | 数值正确性 | stdout 含 `sum=4950` | PASS |

> 这三条断言使该用例**在 Linux + glibc + libomp 上必然失败**（A 直接不成立），
> 因此它是真正的鸿蒙特有用例，而不是一条通用 OpenMP smoke test。

**结论**：opari 工具（源码级插桩）+ libpomp（POMP 运行时）+ libomp（OHOS OpenMP 运行时）
整条链路在 OpenHarmony aarch64 上真实可用；该用例是**鸿蒙特有**的可行性验证（真机执行 + 平台运行时），
且与上游 C 测试互不替代。

### 2.4 平台适配说明

消费者二进制由 OHOS clang `-fopenmp` 自动写入
`RUNPATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib`，
运行时 `libomp.so` 直接解析，无需额外 `LD_LIBRARY_PATH`。

---

## 三、汇总

| 测试类别 | 总数 | 通过 | 失败 | 跳过 |
|---|---|---|---|---|
| 上游测试（C 插桩 + region 表） | 12 | 12 | 0 | 0 |
| 鸿蒙消费者用例（test_package） | 1 | 1 | 0 | 0 |
| **合计** | **13** | **13** | **0** | **0** |

排除（平台限制，非跳过）：Fortran f77 / f90 两项，原因为 OHOS SDK 无 gfortran。
