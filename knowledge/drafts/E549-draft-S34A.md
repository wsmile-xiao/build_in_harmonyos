# E549 — 无主构建系统上游的 shell configure 测试套件在 OHOS 的全量复现

> 状态：草稿（draft）。触发实例：stats 3.4.0（feat/stats-3.4.0）。
> 相似条目查重：E257（header-only 无构建系统的配方完整性，no-op build，不解决测试复现）、
> E307（header-only compile-only 测试）、E321/E322（上游本身有 CMake 的 header-only 迁移）。
> 本条目新增价值：上游连主构建系统都没有、测试为"shell setup + configure.in + 独立 .cpp 程序"
> 时，如何不改上游源码在 OHOS 上复现全量测试，并在 `conan create` 内自包含固化。

## 可复现症状（稳定错误签名）

在 OHOS（无 g++、无 BLAS/LAPACK）按上游文档跑 kthohr/stats 的测试套件：

```text
clang++ ... dbern.cpp -o dbern.test -lblas -llapack
ld.lld: error: unable to find library -lblas
ld.lld: error: unable to find library -llapack
make: *** [Makefile:31: dbern.test] Error 1
```

先行的姊妹症状（CXX 未覆盖时）：

```text
make: g++: not found   →   make: *** [dbern.test] Error 127
```

依赖头文件路径未给时：

```text
fatal error: 'stats.hpp' file not found / cannot find the GCEM library header files.
```

## 根因与最小复现

`tests/test_setup/configure.in`（每个套件复制一份）在非 darwin 平台硬编码：

```bash
if [ -z ${CXX+x} ]; then CXX=g++ ; fi          # 行 45-47
STATS_BLAS_LAPACK="-lblas -llapack"            # 行 167-176（非 darwin 默认）
```

最小复现：`cd tests/dens && bash ./configure -s && make`（无任何环境变量）。
链接失败与库本身无关——stats 是纯头文件库，本体不引用 BLAS/LAPACK 符号；
失败完全来自测试套件默认值。

## 已尝试方案（含失败方案）

| 方案 | 结果 |
|------|------|
| 直接 `./configure && make`（上游文档默认） | ❌ Error 127（g++ 不存在） |
| 仅 `CXX=clang++ ./configure && make` | ❌ `unable to find library -lblas`（默认仍链 blas/lapack） |
| 打补丁改 configure.in | 未采用——发现 configure 支持环境变量钩子，无需补丁 |
| **`CXX=clang++ STATS_MATRIX_OPS="" ./configure -s`** | ✅ 设备上 84/84 全部通过（upstream-tests.log） |

## 最终方案与真实验证

1. **探索阶段（设备，按上游文档等价复现）**：
   `GCEM_INCLUDE_PATH=<gcem-include> CXX=clang++ STATS_MATRIX_OPS="" bash ./configure -s -o "-O2 -DNDEBUG"`
   后 `make -j1`，运行 84 个 `*.test`——84/84 通过、0 失败、0 跳过。
2. **固化阶段（conanfile build()，conan create 内自包含）**：
   - 用 `save()` 生成 CMake driver：每个测试程序一条 `add_executable`（**绝对路径**，
     driver 位于 build 子目录时相对路径会解析失败），`target_include_directories`
     同时指向 source 的 `include/` 与依赖包（gcem）的 `include/`；
   - `cmake.build()` 后逐个 `self.run()`，以进程退出码为断言（rand 套件为统计打印，
     上游本身无硬断言，退出码即上游语义）；
   - `package()` 必须同时拷贝 `*.hpp` 与 `*.ipp`（该族 include 树 145 hpp + 83 ipp，
     只拷 hpp 时消费者报 `fatal error: 'dbern.ipp' file not found`）。

真实验证：`ohc-run.py conan-verify stats 3.4.0` 全门禁 PASS，conan create 日志含
`STATS_UPSTREAM_TEST[1/84]..[84/84]` 全部通过，test_package 消费者测试
（dnorm/pnorm/qnorm/dpois 数值断言 + 固定种子 rnorm 均值校验）通过。

## 适用范围、反例与解除条件

- 适用：kthohr 系（stats/gcem/quickstats 共用该测试骨架）及一切"无主构建系统 +
  shell configure 测试套件"的上游；交叉环境无 g++/BLAS 时。
- 反例：上游测试套件若真实验了 BLAS 路径（`-m "-lopenblas"` 显式传入且被测代码
  调用 blas 符号），置空 `STATS_MATRIX_OPS` 会改变被测语义，此时应改走
  `tool_requires`/依赖注入提供 OpenBLAS，而不是置空。
- 解除条件：上游未来若把 tests 迁到 CMake/CTest，本条目降级为历史参考（同 E321 口径）。

## 风险与禁止策略

- 禁止为消除 `-lblas` 链接错误给 stats 包加 blas 依赖（错误归因，R36 风险）。
- 禁止不改 `package()` 的 `*.ipp` 拷贝而只在 test_package 里绕过。
- configure 是否支持某环境变量必须先 `grep` configure.in 实证（`CXX`、
  `STATS_MATRIX_OPS`、`GCEM_INCLUDE_PATH` 均为该模板实测钩子），不可假设其他
  上游的同名变量存在。
