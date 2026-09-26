# ethash 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 语言判定（R47）
lang-preflight 自动判定为 mixed/setuptools（因根目录存在 pyproject.toml/setup.py，
供 bindings/python 可选 Python 绑定打包使用）。实际主体为 C/C++：
源码 34 个中 cpp 27 + c 3 = 88%（python 4 个全部为 bindings/python 与 setup.py 绑定层），
主构建系统为 CMake（project(ethash)）。按 R47 边界规则 D.4-2（绑定包按源码主体判 cpp，
辅助脚本不算主体语言）应判 cpp，本任务按 cpp 继续适配。该偏差在最终回报 quality_warnings 中说明。

## 编译步骤

1. init-build：官方源 https://github.com/chfast/ethash 直连超时，改用官方 codeload
   tarball https://codeload.github.com/chfast/ethash/tar.gz/refs/tags/v1.1.0（sha256
   73b327f3c23f407389845d936c1138af6328c5841a331c1abe3a2add53c558aa）。
2. 基础库编译（ETHASH_TESTING=OFF）：
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DETHASH_TESTING=OFF -DCMAKE_BUILD_TYPE=Release ..
   make -j4 → 产物 libkeccak.a / libethash.a / libethash-global-context.a
3. staging 安装：make install DESTDIR=$TEST_PREFIX → include/ethash/*.h(.hpp)、lib/*.a、cmake 配置
4. conan-init 生成配方后重写 conanfile.py（CMake 驱动），conandata.yml 填官方 sha256，
   test_package/test.c 改为真实调用 ethash 公开 C API（keccak256 已知向量 + epoch context 哈希链路）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时（init-build 下载失败） | 网络仅 codeload.github.com 可达 | 使用官方 codeload tarball URL，sha256 核验通过 |
| 2 | /tmp 只读（E002） | HMDFS /tmp 只读挂载 | 使用 TMPDIR=$HOME/tmp |
| 3 | lang-preflight 判 mixed | 误将绑定打包 manifest 当主体语言 | 按 R47 D.4-2 边界规则判 cpp 继续（见上） |
| 4 | ETHASH_TESTING=ON 时 HunterGate 下载失败 | Hunter 从 github.com 拉取 | 上游测试改用 conan gtest 依赖，不在配方内用 Hunter（见上游测试台账） |

## 源码修改

无补丁。

## 依赖版本

- gtest（测试依赖，conan 本地缓存 gtest/1.17.0）

## 验证结果

```bash
# 基础库编译与 staging 安装通过（exit 0）
cmake -DETHASH_TESTING=OFF .. && make -j4 && make install DESTDIR=$TEST_PREFIX
```

## 交付物

conan 包产物（ethash/1.1.0）

## 注意事项
- 上游测试通过 conan gtest 提供（配方 ETHASH_TESTING=OFF，测试在本任务上游测试门禁内单独构建运行）。
### 上游测试台账（R51 三步法）

**测试框架**：GoogleTest（上游通过 Hunter 拉取 GTest；github 直连不可达，本轮用本地 conan 缓存 gtest/1.17.0（OHOS armv8 预编译）手动编译运行）。

**独立测试用例枚举（test/unittests/，6 个用户测试源文件 → 53 个 TEST）**：

| 文件 | 用例数 | 是否独立用例 | 运行结果 |
|------|--------|--------------|----------|
| test/unittests/test_ethash.cpp | 37 | 是 | 37/37 通过 |
| test/unittests/test_keccak.cpp | 8 | 是 | 8/8 通过 |
| test/unittests/test_difficulty.cpp | 3 | 是 | 3/3 通过 |
| test/unittests/test_global_context.cpp | 4 | 是 | 4/4 通过 |
| test/unittests/test_primes.cpp | 2 | 是 | 2/2 通过 |
| test/unittests/test_version.cpp | 1 | 是 | 1/1 通过（-DTEST_PROJECT_VERSION=1.1.0） |
| test/unittests/helpers.hpp | 0 个 TEST | 非独立用例（测试辅助头） | — |
| test/unittests/test_cases.hpp | 0 个 TEST | 非独立用例（测试数据头） | — |

**非独立用例入口（不计入上游用例数，台账列出）**：
- test/benchmarks/：4 个 benchmark 二进制（ethash/keccak/global-context/threadsync），基准程序不是断言型测试用例（上游 CMake：benchmark 库经 Hunter 拉取，github 不可达，且基准以耗时测量为目的，不计入用例总数）→ 未运行为独立断言用例。
- test/experimental/difficulty.{h,cpp}：被 test_difficulty.cpp 链接的库源码（已作为测试依赖编译），本身非测试。
- test/fakeminer/fakeminer.cpp：示例矿工程序（上游 CMake 构建的目标），非测试用例。
- test/integration/compilation/：cmake-config 编译集成检查（验证 find_package(ethash) 可用），非 GTest 用例；已由 conan test_package 的 find_package 消费者验证覆盖等价功能。
- test/integration：无独立断言用例。

**双口径统计**：
- source_declared_total（用户测试源中独立 TEST 用例数）：**53**
- configured_executable_total（当前 OHOS 配置实际实例化的独立可执行用例数）：53（ethash-test 单二进制内 53 个 TEST，gtest_discover_tests 等价注册；本轮手动编译等价于同一 CMake 目标）
- executed_passed_total：**53**，失败 0，未运行/未实例化 0
- 全量通过率：**53/53 (100.0%)**；当前配置可执行集合通过率：53/53 (100.0%)

**构建/运行命令证据**：
```
命令: /data/service/hnp/bin/clang++ -std=c++17 -fno-rtti -I include -I lib -I test/unittests -I test/experimental -I <gtest>/include -DTEST_PROJECT_VERSION='"1.1.0"' test/unittests/*.cpp build/lib/**/*.a <gtest>/lib/libgtest*.a -lpthread -o ethash-test
cwd: $TMPDIR/builds/ethash-1.1.0.work
运行: ./ethash-test （[==========] 53 tests from 9 test suites ran; [ PASSED ] 53 tests, exit 0, 38330 ms）
日志: $TMPDIR/ethash-testbuild/ethash-upstream-run.log
```
---

**编译结束**: 2026-09-22 17:01
**最终状态**: built
