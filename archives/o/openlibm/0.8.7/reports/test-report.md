# openlibm 0.8.7 上游测试报告（复核升级）

## 复核信息

- **软件**: openlibm 0.8.7（上游 tag v0.8.7，sha256=e328a1d59b94748b111e022bca6a9d2fc0481fb57d23c87d90f394b559d4f062 已核验）
- **复核日期**: 2026-09-27
- **平台**: HarmonyOS PC (aarch64-unknown-linux-ohos)
- **编译器**: OHOS SDK clang 15.0.4（Target: aarch64-unknown-linux-ohos）
- **辅助工具**: llvm-ar / llvm-ranlib / GNU make 4.4.1
- **构建系统**: Makefile（Makefile + Make.inc，无 configure）

## 上游测试运行

### 运行命令

```bash
# 在源码根目录（openlibm-0.8.7）执行上游测试套件
make test CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib -j2
```

`make test` 目标串联：`test/test-double` → `test/test-float`（根 Makefile `check: test/test-double test/test-float` 依次运行两者）。

> 说明：v0.8.7 无 regression 测试目录；`test/inf_torture.c` 与 `test/libm-bench.cpp` 未接入上游 `check` 目标（inf_torture 是 NaN 折磨测试、libm-bench 是基准程序，均非测试套件）。

### 测试结果汇总

| 测试程序 | 用例数 | 异常标志用例 | 结果 |
|----------|--------|--------------|------|
| test-double | 1118 | 932 | ✅ 全部通过 |
| test-float | 1101 | 923 | ✅ 全部通过 |

**实测结果: 4074/4074 通过（100%），0 失败**

- test-double: 1118 用例 + 932 异常标志 = 2050
- test-float: 1101 用例 + 923 异常标志 = 2024
- 合计: 4074

### 关键日志行（实测输出）

```
Test suite completed:
  1118 test cases plus 932 tests for exception flags executed.
  All tests passed successfully.            # test-double

Test suite completed:
  1101 test cases plus 923 tests for exception flags executed.
  All tests passed successfully.            # test-float
```

## test_package 鸿蒙专项测试

- **源文件**: `test_package/test.c`（3 组断言：sin(pi)≈0、cos(pi)≈-1、log(e)≈1）
- **结果**: 断言全部通过；conan create 内嵌 ctest 1/1 通过
- 实测运行输出：`openlibm 0.8.7 test: sin(pi)=0.000000 cos(pi)=-1.000000 log(e)=1.000000 OK`

```
1/1 Test #1: test_openlibm ....................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```

## Conan 配方验证（W3）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- **exit code**: 0
- **构建产物**: lib/libopenlibm.a（静态，默认 shared=False）+ include/openlibm/*.h + lib/pkgconfig/openlibm.pc
- **test_package**: ctest 1/1 通过（test_openlibm 链接 libopenlibm.a 并运行数值断言）
- 配方符合 R33（编译器取自 conf）、R34（test_package 实质调用被测包 API）、R26 思路（默认静态构建，规避 HMDFS 动态库加载问题）

## 结论

上游测试 **4074/4074 通过（100%）**（test-double 2050 + test-float 2024，0 失败）；鸿蒙专项 test_package 断言全过、ctest 1/1 通过；conan create 完整构建+测试验证通过（package revision 8a65d4d3584d1aa6f319e638644f383f）。
