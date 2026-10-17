# srs-state 1.9.5 上游测试报告

- 测试日期: 2026-10-08
- 平台: HarmonyOS PC (OpenHarmony, aarch64, os=OHOS), clang 15.0.4
- 上游版本: ossrs/state-threads v1.9.5 (sha256 1fb10632fd047f7b274845e4047ea1e3379dbdf430c58fe3fe910b81c742d030)

## 上游测试入口核验

- 测试源: 源码树 `utest/`（st_utest.cpp / st_utest_coroutines.cpp / st_utest_tcp.cpp），
  内置 gtest-fit（googletest 源码捆绑），无 ctest/pytest/automake check 注册。
- 官方运行方式: 仓库根 `Dockerfile.test` → `make linux-debug-utest && ./obj/st_utest`（即上游唯一测试入口）。
- test_package 不替代上游测试统计（消费者测试单独汇报，见 §3）。

## 1. 上游测试实测（真实执行）

| 项 | 值 |
|---|---|
| 构建命令 | `make -j1 linux-debug-utest STATIC_ONLY=yes TARGETDIR=LINUX_OHOS_OPT CC=clang CXX=clang++ AR=llvm-ar RANLIB=ranlib LD=clang LDFLAGS='-shared -Wl,-soname,libst.so.1 -lc'` |
| 运行命令 | `./obj/st_utest` |
| 用例总数 | 7 |
| 通过 | 7 |
| 失败 | 0 |
| 跳过 | 0 |
| 断言数 | 25 |
| 退出码 | 0 |

用例明细（全部 PASS）：

| # | 用例 | 套件 | 结果 |
|---|---|---|---|
| 1 | ExampleIntSizeTest | SampleTest | PASS |
| 2 | StartCoroutine | CoroutineTest | PASS |
| 3 | StartCoroutineX3 | CoroutineTest | PASS |
| 4 | StartCoroutineAdd | CoroutineTest | PASS |
| 5 | StartCoroutineAddX3 | CoroutineTest | PASS |
| 6 | StartCoroutineParams | CoroutineTest | PASS |
| 7 | TcpConnection | TcpTest | PASS |

gtest 汇总原文: `[==========] 7 tests from 3 test suites ran.` / `[  PASSED  ] 7 tests.`

## 2. conan create 内的上游测试（层 1 集成）

conanfile.py build() 末尾执行同一入口；`reports/conan-create.log` 内嵌证据：
`RUN: make -j1 linux-debug-utest ...` → `RUN: ./obj/st_utest` → `[  PASSED  ] 7 tests.` → `Package '21b17f8b2bc0e9511e276e3d57a23893067cefe5' created`。

## 3. 消费者测试（test_package，层 2）

| # | 测试 | 断言 | 结果 |
|---|---|---|---|
| 1 | srs_state_consumer（test.c：st_init/协程创建/Join/参数传递/协作式调度） | 7 | Passed (0.03s) |
| 2 | srs_state_ohos_consumer（test_srs_state_ohos.c，**鸿蒙新增用例**：`#ifndef __OHOS__ #error` 守卫 + AArch64 ABI 断言 + OHOS 协程调度 + 单调时钟） | 8 | Passed (0.07s) |

ctest 汇总: `100% tests passed, 0 tests failed out of 2`。

## 日志留存说明

- reports/conan-create.log / reports/conan-verify-report.md：随 PR 提交。
- 原始日志（本地产物，未随 PR 提交）：`$TMPDIR/builds/srs-state-1.9.5.work/{build-explore3.log, utest-build.log, utest-run.log}`、`$TMPDIR/conan-create-srs-state.log`、`$TMPDIR/conan-verify-srs-state.log`、`$TMPDIR/finish-srs-state.log`（$TMPDIR=/data/storage/el2/base/cache）。

## 复现方式

```bash
conan create archives/s/srs-state/1.9.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 上游测试单独复现（解压源码后）:
make linux-debug-utest STATIC_ONLY=yes TARGETDIR=LINUX_OHOS_OPT CC=clang CXX=clang++ AR=llvm-ar RANLIB=ranlib LD=clang
./obj/st_utest
```
