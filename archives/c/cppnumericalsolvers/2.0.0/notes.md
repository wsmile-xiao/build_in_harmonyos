# cppnumericalsolvers 2.0.0 适配笔记

## 编译环境
- 构建系统: header-only（上游 CMake + Bazel；适配侧直接 clang++ 编译测试/消费者）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++
- 标准: C++17
- 状态: built

## 官方来源
- 上游: https://github.com/PatWie/CppNumericalSolvers (tag v2.0.0)
- 源码 tarball SHA-256: `a00caec48809a2315497f3a8436a07ccbf5d9cb1234ed039a3c78b27ad94daae`
- 污染扫描: conandata.yml/conanfile.py/源码无 file://、.build-cache、predl_cache、currentUser、本机绝对路径命中

## 编译步骤

```bash
# 语言预检 (R47)
python3 scripts/ohc-run.py lang-preflight cppnumericalsolvers 2.0.0 --src <src>  # ✅ cpp 匹配

# 上游测试直接编译（header-only，无需 configure；include 根 = <repo>/include）
clang++ -std=c++17 -O1 -I<repo>/include -I<eigen>/include/eigen3 -I<gtest>/include \
    src/test/<file>.cc -L<gtest>/lib -lgtest [-lgtest_main] -pthread -o <bin>
```

## 上游测试完整枚举台账（双口径）

### 源码声明口径 (source_declared_total = 64)

| 测试源文件 | 独立用例声明 | 用例明细 | 分类理由 |
|---|---|---|---|
| src/test/verify.cc | 17 | 7×SOLVER_SETUP×2(Far/Near)=14 + CentralDifference Gradient/Hessian 2 + Constrained Simple 1 | TYPED_TEST 宏展开，TypeParam=double，实际 17 实例 |
| src/test/cstep_test.cc | 7 | CstepCase1-4 + CstepClamp + CstepSafeguard + CstepInvariants | 独立 TEST() |
| src/test/hager_zhang_test.cc | 4 | HagerZhangCase1-4 | 独立 TEST() |
| src/test/trust_region_newton_test.cc | 9 | StrictlyConvex/Rosenbrock/BoundaryExit/Indefinite/Interior/Quartic/MaxRadius/GradientNormStop/IterationLimit | 独立 TEST() |
| src/test/augmented_lagrangian_test.cc | 27 | Quadratic* 9 + ToAugmentedLagrangian 3 + KKT 3 + Outer 7 + Constrained 2 + FunctionExpr 1 + NonConvex 2 + Box 1 | 独立 TEST() |
| **合计** | **64** | | |

### 配置/实例化口径 (configured_executable_total = 5 可执行 / 64 用例)

| 构建目标 | 上游注册 | 实例化用例 | 实际运行 |
|---|---|---|---|
| verify | CMake build_test(verify) + Bazel build_test("verify") | 17 | ✅ 17/17 |
| cstep_test | CMake build_test(cstep_test) + Bazel build_test("cstep_test") | 7 | ✅ 7/7 |
| hager_zhang_test | Bazel build_test("hager_zhang_test")（CMake 未注册） | 4 | ✅ 4/4 |
| trust_region_newton_test | Bazel build_test("trust_region_newton_test")（CMake 未注册） | 9 | ✅ 9/9 |
| augmented_lagrangian_test | Bazel build_test("augmented_lagrangian_test")（CMake 未注册） | 27 | ✅ 27/27 |
| **合计** | | **64** | **64/64 = 100%** |

- 双口径：源码声明 64 个独立用例 = 当前配置实际实例化并运行的 64 个用例，`64/64 (100.0%)`（全量通过率与当前配置可执行集合通过率一致）。
- 差异说明：上游 `src/test/CMakeLists.txt` 仅注册 verify + cstep_test（CMake 配置过时），Bazel `BUILD` 完整注册全部 5 个测试；适配侧按 Bazel 全量实例化编译运行，无未实例化/未运行用例。
- 框架内部宏、SECTION 子节、样例/基准不计入独立用例：src/examples/*.cc 是样例非测试，benchmark 不存在（2.0.0 无 benchmark.cpp）。

### 运行证据

| 入口 | 命令（cwd=src/test 目录） | 退出码 | 通过 | 日志 | SHA-256 |
|---|---|---|---|---|---|
| verify | `clang++ ... verify.cc -lgtest -pthread -o verify && ./verify` | 0 | 17/17 | /storage/Users/currentUser/tmp/logs-cppnumericalsolvers-2.0.0/verify_run.log | 634b976f4fddd280e333ce81ffcb18b24364326940d93101097b6052cb572cf4 |
| cstep_test | `clang++ ... cstep_test.cc -lgtest -lgtest_main -pthread -o cstep_test && ./cstep_test` | 0 | 7/7 | .../cstep_test_run.log | 2e2c0c8041058290d2903266b019f5949f68c671c01b6540a7d6e4cc4ce3910f |
| hager_zhang_test | `clang++ ... hager_zhang_test.cc -lgtest -lgtest_main -pthread -o hager_zhang_test && ./hager_zhang_test` | 0 | 4/4 | .../hager_zhang_test_run.log | f8417a2e5380982f1d0a2b0a9d5cedfae5b2e7c78416ba9281526d3d0f8f33eb |
| trust_region_newton_test | `clang++ ... trust_region_newton_test.cc -lgtest -pthread -o trn_test && ./trn_test` | 0 | 9/9 | .../trn_test_run.log | fd8b4e5e9ba901d33459eaa2381f1627ee44c6b6293403410e992da3c02d9084 |
| augmented_lagrangian_test | `clang++ ... augmented_lagrangian_test.cc -lgtest -pthread -o aug_lag_test && ./aug_lag_test` | 0 | 27/27 | .../aug_lag_test_run.log | d5214750a300f2a2536d06241a3fd8e60bdb611d4ac910141357a620f0ffb6b2 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时（<urlopen error timeout>） | 网络环境访问 github.com 受限 | 改用 GitHub 官方下载域 codeload.github.com 下载同一 tag tarball；conandata.yml 记录官方 github.com archive URL（CI 自动加镜像 fallback） |
| 2 | 测试编译 `cppoptlib/function.h not found` | 测试文件以 `<repo>/include` 为 include 根 | include 根用 `-I<repo>/include`（与上游 Bazel `includes=["."]` 一致），编译通过 |
| 3 | 上游 CMake 测试注册不全（仅 verify/cstep_test） | CMakeLists 未同步新增 3 个测试文件 | 按 Bazel BUILD 全量注册口径直接编译运行全部 5 个测试入口，无未实例化项 |

## 依赖版本

| 依赖 | 版本 | 用途 | 制品仓状态 |
|---|---|---|---|
| eigen | 3.4.1 | 线性代数（头文件） | ✅ ohpcd 已发布 |
| gtest | 1.17.0 | 上游测试框架（test_requires） | ✅ ohpcd 已发布 |

## 验证结果

```bash
# 5 个上游测试入口全部编译运行，64/64 通过 (100%)
verify 17/17 | cstep_test 7/7 | hager_zhang_test 4/4 | trn_test 9/9 | aug_lag_test 27/27
# 鸿蒙专项测试 + test_package + 消费者验证：见 test_package/ 与 reports/
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 配方（package_id clear，依赖 eigen，test_requires gtest） |
| conandata.yml | 官方 github.com archive URL + sha256 |
| test_package/ | 消费者式 test_package（编译+运行调用公开 API） |
| test_package/test_cppoptlib.cpp | 鸿蒙专项消费测试源码 |
| reports/ | 验证报告 |

## 注意事项

- 纯 header-only 库（include/cppoptlib 全部模板实现），无 .so/.a 产物，非 CLI 库，不生成 commands.json。
- 系统无同名库（cppnumericalsolvers），无需静态链接隔离。
- 任务为【知识库扩展】路径 B：知识候选台账与七轴查重见 reports/knowledge-candidate-ledger.md。
---

**编译结束**: 2026-09-25 23:03
**最终状态**: built
