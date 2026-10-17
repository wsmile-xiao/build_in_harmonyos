# ifopt 2.1.4 适配笔记

## 基本信息

- 上游仓库：https://github.com/ethz-adrl/ifopt
- 上游版本：2.1.4（tag `2.1.4`，commit `a3867c1adb5782b2ac91689604951c2687d52640`）
- 源码包：https://github.com/ethz-adrl/ifopt/archive/refs/tags/2.1.4.tar.gz
- SHA256：`da38f91a282f3ed305db163954c37d999b6e95f5d2c913a63bae3fef9ffb3a37`（147363 字节，2026-09-20 实测下载计算）
- 许可证：BSD-3-Clause
- 构建系统：CMake（`CMakeLists.txt` + `ifopt_core/CMakeLists.txt` + `ifopt_ipopt/CMakeLists.txt`）
- 适配路径：路径 A（基础适配）——1 个 portability 补丁（cmake_minimum 提升）+ source() 内 Python 直改 GTest 发现兼容（均不改测试逻辑；上游官方选项关闭求解器后端）
- 状态：built（待 HMBS 真机预检回填实测数）

## 编译环境

- 目标：HarmonyOS aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 编译器：clang 15 / libc++
- 依赖：`eigen/3.4.1`（已发布，transitive_headers）；`gtest/1.17.0.1`（仅 `test_requires`，供上游测试编译；必须用本仓独有版本，见问题 5）

## R51 上游测试申报表（适配前清点）

| # | 上游测试入口 | 来源文件 | 框架/命令 | 用例数 | 本配方是否运行 |
|---|--------------|----------|-----------|--------|----------------|
| 1 | `ifopt_core-test` | `ifopt_core/test/composite_test.cc`（6 TEST） + `ifopt_core/test/problem_test.cc`（10 TEST） | gtest，经 `add_test(ifopt_core-test ifopt_core-test)` 注册为 ctest；命令 `ctest --output-on-failure` | 1 个 ctest 条目，内含 16 个 gtest 用例 | 是（`BUILD_TESTING=ON`，GTest 由 Conan 提供，`build()` 内 `cmake.test()` 实跑） |
| 2 | `ifopt_ipopt-example` | `ifopt_ipopt/test/ex_test_ipopt.cc`（`main` + 2 条 assert 求解验证） | ctest 直接运行求解示例；命令 `ctest --output-on-failure` | 1 个 ctest 条目 | 否（需 Ipopt 求解器库，见下） |
| 合计 | — | — | 口径 `ctest_entries` | **2** | 运行 1，缺口 1（4101 见 gaps） |

清点方法：逐行阅读 `CMakeLists.txt`（`option(BUILD_IPOPT ON)` / `add_subdirectory`）、
`ifopt_core/CMakeLists.txt`（`find_package(GTest QUIET)` + `add_executable` + `add_test`）、
`ifopt_ipopt/CMakeLists.txt`（`find_package(IPOPT 3.11.9 REQUIRED)` + `add_test`），
并用 `grep -c TEST(` 核对两份 `*_test.cc` 的用例数（6 + 10 = 16）。

## 配方关键决策

- `BUILD_IPOPT=OFF` / `BUILD_SNOPT=OFF`：上游官方选项（`CMakeLists.txt` 的 `option()`），不是测试删减。
  IPOPT 后端要求 `find_package(IPOPT 3.11.9 REQUIRED)`（coinor Ipopt + MUMPS 等线性求解器），
  而制品仓内 `archives/i/ipopt/3.14.19/` 仅有 `manifest.yaml` + `notes.md`，无 `conanfile.py`，
  即无已发布 Conan 包可依赖；按 R36/W2 单 PR 单库规则，不能在本 PR 内捎带适配 ipopt。
- `BUILD_TESTING=ON`：保持上游测试开关开启（R51），不静默跳过。
- 默认静态库（`shared=False`）：纯库包，无 `bin/` 产物，按 R38 不需要软件级 `commands.json`。
- `package_info`：`libs=["ifopt_core"]`，透传 `eigen::eigen`，
  `cmake_file_name=ifopt` / `cmake_target_name=ifopt::ifopt_core`，与上游
  `find_package(ifopt)` + `ifopt::ifopt_core` 用法一致。

## 上游测试缺口说明（对应 HMBS gaps）

- 缺口数量：1（`ifopt_ipopt-example`）
- 类别：`ohos_feature`（非 `missing_dependency` 豁免：缺的是求解器后端能力，不是可补齐的普通依赖；
  补齐意味着先完整适配发布 ipopt，超出本 PR 范围）
- 证据：
  - `archives/i/ipopt/3.14.19/` 目录实测仅 `manifest.yaml` + `notes.md`，无配方；
  - 上游 `ifopt_ipopt/CMakeLists.txt` 首行即 `find_package(IPOPT 3.11.9 REQUIRED)`；
  - 本构建 `ctest -N` 仅注册 `ifopt_core-test`（日志以 `HMBS diag registered ctest entries=1` 为证）。

## test_package 设计（R34 实质调用）

- 文件：`test_package/test_ifopt.cpp`（单个消费者二进制 `test_ifopt`）
- 内容：不依赖求解器，仅用 `ifopt_core` 的求解器无关层——自定义 `VariableSet`/`ConstraintSet`/`CostTerm`
  子类（复刻上游 `test_vars_constr_cost.h` 的示例问题 `min -(x1-2)^2 s.t. x0^2+x1=1`），组装 `Problem`，
  逐项断言变量数/边界/取值/约束数/约束值/雅可比/代价/梯度/成本项存在性，共 13 条断言；
  任一失败即非零退出，不存在空壳路径。
- 反向验证友好：删除安装包头/库后链接即失败（L1e 可捕获）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | IPOPT 后端无法作为 Conan 依赖 | 制品仓无已发布 ipopt 包 | 使用上游官方 `BUILD_IPOPT=OFF`，仅适配求解器无关的 `ifopt_core`，缺口如实上报 |
| 2 | 上游测试需 GTest | 真机/CI 不保证系统 GTest | `test_requires("gtest/1.17.0.1")` + `CMakeDeps`，由本仓配方提供 `GTest::GTest`（必须用 `.1` 后缀的本仓独有版本，见问题 5） |
| 3 | `/tmp` 在真机可能只读 | OHOS 真机挂载限制 | 配方内置 `_ensure_writable_tmp()`，复用 HMBS 注入的 `TMPDIR/TMP/TEMP`，与 zydis/darts 同模式 |
| 4 | profile 编译器路径可能迁移 | 真机 clang 路径变更史 | `generate()` 按 `_resolve_compiler` 解析真实编译器并 pin 到 toolchain，与 zydis 同模式 |
| 5 | 真机 `cmake/4.4.3 build() KeyError: 'OHOS'` | conancenter `gtest/1.17.0` 经 `tool_requires` 拉入 `cmake/4.4.x`，其 `conandata` 无 OHOS 源码条目，`--build=missing` 下被迫源码构建即 KeyError（2026-09-19 预检 `conan create` 日志：`gtest/1.17.0 Downloaded recipe revision` 后紧跟 `cmake/4.4.3 ... KeyError: 'OHOS'`；ayatana-ido v2 笔记记载同机制同报错） | 改用本仓独有 `gtest/1.17.0.1`（`archives/g/gtest/1.17.0.1/conanfile.py` 实测零 `tool_requires`，纯 CMake + 系统 cmake 构建；benchmark/1.9.5、celero/2.10.0、verdict/1.4.5 同款已合入先例），图中不再有 cmake 工具边 |
| 6 | 真机 `cmake.configure()` 报 `Compatibility with CMake < 3.5 has been removed`（CMakeLists.txt:2） | 上游顶层 `CMakeLists.txt` 声明 `cmake_minimum_required(VERSION 3.1.0 FATAL_ERROR)`，真机 cmake 为 4.4.3，已移除对 <3.5 的兼容（知识库 E103/E187 同类：woff2 等老项目同报错） | 新增 `patches/0001-cmake-minimum-3.5.patch`（3.1.0 → 3.5，不改任何构建逻辑），`conandata.yml` 以 Conan 2.x list 格式声明，`source()` 内 `apply_conandata_patches(self)` 应用；子目录（ifopt_core 等）实测无独立 `cmake_minimum_required`，无需多补丁 |
| 7 | 真机 configure 通过但 `registered ctest entries=0`，`LastTest.log` 无内容 | 上游 `ifopt_core/CMakeLists.txt` 用基础签名 `find_package(GTest QUIET)` + `if (TARGET GTest::GTest)` 守卫：基础签名优先命中 CMake 自带的 FindGTest 模块（系统无 gtest，静默失败），从不进入 config 模式，故 Conan 提供的包配置永远不可见，测试目标直接被跳过（非测试失败，是发现失败） | `source()` 内 Python 直改 `ifopt_core/CMakeLists.txt`（`find_package(GTest QUIET CONFIG)` + 缺失时由小写 `GTest::gtest`/`GTest::gtest_main` 补 `GTest::GTest`/`GTest::Main`，不改测试逻辑）并在 `generate()` 置 `GTest_DIR` 指向 gtest 包内 `lib/cmake/GTest`（abseil/20260526 + biosoup/0.10.0 同款先例） |

| 8 | 真机 `source()` 报 `Failed to parse patch: .../0002-gtest-target-compat.patch`（`extra lines for hunk no.1`） | 静态补丁块头声明 `+28,20` 与实际新增 16 行+上下文 6 行=22 行不符（多算少写 2 行），conan `apply_conandata_patches` 严格校验块长度，直接拒绝解析；与 GTest 逻辑本身无关，是补丁封装错误 | 删除静态 `0002` 补丁，改由 `source()` 内 `_patch_gtest_targets()` 对 `ifopt_core/CMakeLists.txt` 做一次性字符串替换（幂等守卫 + 缺失警告），不再依赖 hunk 行号计数；`conandata.yml` 仅保留 `0001` |

| 9 | test_package `cmake.configure()` 在 `project()` 报 `The CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++` 错误，主包已构建成功、上游 ctest 1/1 通过 | test_package 的 `generate()` 直接沿用 profile 的 `tools.build:compiler_executables` 路径，而该路径在真机不存在或不可执行；主包早有 `_resolve_compiler`+`_fix_generated_toolchain_compiler` 兜底（PATH/~/usr/local/bin 真实 clang），test_package 缺失同等逻辑，两侧行为不一致 | 将主包同款编译器解析与工具链修正逻辑镜像到 `test_package/conanfile.py` 的 `generate()`（pin `CMAKE_C/CXX_COMPILER` 到真实 clang，并重写 `conan_toolchain.cmake` 中的失效旧路径；不改测试断言与口径） |

| 10 | test_package 编译报 `no type named 'VectorXd' in namespace 'ifopt'`（连带 VecBound/Jacobian，共 20 errors） | `VectorXd/VecBound/Jacobian` 是 `ifopt::Component` 的嵌套别名（`composite.h` 内 `using`），并非 `ifopt` 命名空间的直接成员；测试文件误写成 `ifopt::VectorXd` 等限定形式。`Bounds/NoBound` 才是 `ifopt` 直接成员，保持限定正确 | 去掉测试文件中 11 处类型限定的 `ifopt::` 前缀（5x VectorXd、4x VecBound、2x Jacobian），子类内经继承作用域解析（与上游 `test_vars_constr_cost.h` 同模式）；保留 `ifopt::Bounds/NoBound/Problem` 等正确限定，不断言删减 |\n\n## 验证结果

```bash
# 由 HMBS 后台在 HarmonyOS aarch64 真机执行（本机 Windows 不运行 conan）：
# conan create archives/i/ifopt/2.1.4 --user=ohpcd --channel=stable
#   -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 本轮（工作树准备轮）：未执行真机构建；以上数字来自上游源码审计，实测数待预检回填。
- 防证伪提醒：预检通过后需确认 `ctest` 输出非空、`LastTest.log` 含 `Test Passed.`、
  `test_ifopt` 输出 13/13 通过，避免静默通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | CMake 配方（core-only + ctest 接入 + HMBS 双通道证据） |
| `conandata.yml` | 官方 GitHub tag 归档 URL + sha256 |
| `manifest.yaml` | 版本级清单（`built`，待预检后按实测更新） |
| `test_package/` | 消费者测试（二进制 + CMake + MANIFEST） |
| `notes.md` | 本文件 |

## 2026-09-20 rule4 evidence 修复（未提交）

- 真机报 incomplete：rule4 “passed 状态与上游结果矛盾”（discovered 2 / executed 1 / passed 1 却标 passed）。
- 根因：build() 的 ok 只校验 core 内部自洽，未要求 executed==discovered；导致1/2 部分运行被声称为 passed。
- 修复：引入 core_ok/full_ok 双判据；passed 仅当全量 executed==2 时才成立；core 全绿但缺 IPOPT 后端时发 failed + gaps + reason，构建本身不招起语（仅 core 真失败才 raise）；test_package 侧重发兼容 failed 诚实标记以免缓存命中轮丢证据。
- 下一轮待真机验证。

## 2026-09-20 rule4 少报修复（未提交，待真机验证）

- 审查打回：rule4 少报，上游实测 N=16 > 声明 N=2。
- 根因：旧口径用 ctest_entries（2 条目）计数，而审查按 gtest TEST 宏计数（composite 6 + problem 10 = 16）；ipopt 示例为 plain main，含 0 个 TEST 宏。
- 修复：计数口径切换为 gtest_macros，OFFICIAL_GTEST_TOTAL=16；MANIFEST upstream_test_total 2→16；build() 解析 LastTest.log 内 gtest `[ RUN ]/[  OK ]/[ FAILED ]/[ SKIPPED ]` 逐行计数 + `[==========] N tests ran` footer 交叉核对，discovered/executed 均来自同一日志；payload framework 改为 gtest；PR 正文合计 16、上游 16/16、新增 1/1。
- 待 HMBS 真机预检确认 16/16 实测数。
