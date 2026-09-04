# Test Report — effolkronium-random 1.5.0

> 本报告依据 R01/R02 实际执行的命令与日志撰写，不包含虚构测试。
> 生成时间：2026-09-02（R03 local finish closure 阶段）

## 1. 概述

| 项 | 值 |
|----|----|
| 软件 | effolkronium-random |
| 版本 | 1.5.0 |
| 类型 | header-only C++11 库（无编译产物，无 bin/、lib/） |
| 上游仓库 | https://github.com/effolkronium/random |
| 官方 tag | v1.5.0 (commit b9e79f352278f48948689dca74fd27e6821d24e8) |
| 源码 sha256 | c05a042f8daf54913e3a836e10a213bbbeaf09a89630649bd0011fe65eff50d9 |
| Conan profile | ohos-aarch64（os=OHOS, arch=armv8, clang 15, libc++） |

## 2. 上游测试（R01，3/3 通过）

| 项 | 值 |
|----|----|
| 命令 | `cmake -S . -B build-test -DRandom_BuildTests=ON -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang -DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 构建 | `make -j4`（cwd=/storage/Users/currentUser/builds/effolkronium-random-1.5.0.work/build-test，exit 0） |
| 运行 | `ctest --output-on-failure`（cwd 同上，exit 0） |
| 结果 | **3/3 通过（100%）**：random_static_test PASS、random_thread_local_test PASS、random_local_test PASS |

> 说明：上游 CMakeLists 声明 `cmake_minimum_required(VERSION 3.0)`，本机 CMake 4.1.2 已移除 <3.5 兼容，配置阶段加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（未修改上游源码，无补丁）。

## 3. test_package（Conan L1 消费者测试，1/1 通过）

| 项 | 值 |
|----|----|
| 命令 | `conan create ... -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` |
| 运行 | `cmake --build ... --target test`（W3 日志中 1/1 Test #1: test_effolkronium_random Passed） |
| 结果 | **1/1 通过（100%）**，`100% tests passed, 0 tests failed out of 1` |
| L1 证据 | L1a: test_package 由 conan create 执行 ✅；L1b: 测试执行证据存在于日志 ✅ |
| R34 反证 | L1e 破坏性反向验证通过：移除 include/ 后构建失败，证明测试真实依赖被测包 ✅ |

> test.cpp 实质调用 `random_static/random_thread_local/random_local` 的 `get()`（整型/浮点/字符/布尔/initializer_list）、`shuffle()`、`engine()` API 并断言取值范围（约 300 断言）。

## 4. HarmonyOS 专项证据

- 使用 OHOS 适配版 Conan（2.29.1）+ `ci/conan/profiles/ohos-aarch64`（os=OHOS, armv8, clang 15, libc++），conan create 在 OHOS profile 下成功。
- CMakeToolchain 自动映射 `CMAKE_SYSTEM_NAME=HarmonyOS`；测试二进制以 clang 15 (aarch64-linux-ohos) 编译并通过。
- header-only 库无 bin/lib 产物：G3 无系统同名库冲突、L2 smoke test 跳过（无 bin/）、L5 基线产物 warn（无产物，header-only 预期行为）。
- 平台适配：无源码修改、无补丁（纯头文件，C++11 标准库实现），无需要 `#ifdef __OHOS__` 的实质平台逻辑。

## 5. W3 本地 CI 模拟（R02 隔离后 1/1 通过）

| 项 | 值 |
|----|----|
| 命令 | `zsh ci/conan/build_and_test.sh archives/e/effolkronium-random/1.5.0`（脚本 shebang 为 zsh） |
| setup.sh | exit 0 |
| build_and_test.sh | exit 0，**1/1 package 通过，Pass rate 100%** |
| L0 | pass（含 L0j 版本冲突、L0k commands.json、L0m 目录结构、JC junk gate） |
| JC | JC_RESULT=pass（R02 对 7 个其他库历史 baseline 条目做 index-only 隔离后不再误报） |
| L1 | pass（test_package 执行 + R34 反证） |
| L2/L4/L5 | skip/warn（header-only 无 bin/ 产物，预期） |

> R01 的 W3 曾因 7 个其他库在 main 上被跟踪的历史 junk 文件（flatcv/goaccess/captagent/lsof/scudo-malloc/stb_image）被 JC full 模式误报；R02 按任务授权对这些条目做临时 index-only 隔离后 W3 通过，并在 R02 结束前全部恢复。

## 6. 未运行 / 不适用项

| 项 | 状态 | 说明 |
|----|------|------|
| make check 上游全量测试 | 不适用 | 上游无 make check；测试由 CMake/ctest 驱动（见 §2） |
| L2 smoke test（--version） | 跳过 | header-only 无 bin/ 可执行产物 |
| L5 产物基线（bin/lib） | warn | 无产物，header-only 预期行为 |
| packaging/*.tar.gz | 未创建 | header-only 无二进制制品；如门禁要求将在后续按框架规则处理 |
| finish 终态 | 待执行 | 本报告编写时 finish 尚未在本轮（R03）执行，不预先声明其通过 |

## 7. 结论

上游测试 3/3、test_package 1/1、W3 1/1 均以真实命令执行并有日志追溯（conan-verify-report.md、conan-create.log、w3-local-ci.log）。无伪造测试；finish 终态以实际执行结果为准。
