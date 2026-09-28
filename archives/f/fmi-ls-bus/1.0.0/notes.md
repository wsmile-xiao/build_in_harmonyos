# fmi-ls-bus 1.0.0 适配笔记

## 编译环境
- 构建系统: headeronly（纯头文件 C API，无编译产物；构建入口为 tests/CMakeLists.txt 头测试）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

```bash
# 1. 官方源码核验（tag v1.0.0 → commit 8abdf039）
#    url: https://github.com/modelica/fmi-ls-bus/archive/refs/tags/v1.0.0.tar.gz
#    sha256: c72ea6bcb04e033bb11720dba66e292eb2e6557e8bc0a8262acdeb79504c58f2

# 2. 上游头测试构建（OHOS 工具链 + conan GTest 1.17.0.2）
cmake -S tests -B build -DCMAKE_TOOLCHAIN_FILE=.../conan_toolchain.cmake \
      -DCMAKE_PREFIX_PATH=.../gtest-prefix -DMODULE_LIST=can -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --output-on-failure  -> 130/130 Passed

# 3. 鸿蒙专项测试（tests 之外新增，独立于上游测试）
clang++ -std=c++17 -O2 -I headers -I fmi-standard/headers \
        -o fmi_3_ls_bus_ohos_test fmi_3_ls_bus_ohos_test.cpp
./fmi_3_ls_bus_ohos_test -> 7/7 checks passed

# 4. conan-init + conan-verify（G1-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-init fmi-ls-bus 1.0.0
python3 scripts/ohc-run.py conan-verify fmi-ls-bus 1.0.0
# conan create 内 test_package 消费者用例：8/8 consumer checks passed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连不可达 | 本机仅 api.github.com 可达 | 经 GitHub API 官方端点下载 tarball，后核验官方 archive URL 字节并取真实 SHA-256 |
| 2 | api tarball 与 archive URL 字节不同 | GitHub 两端点 gzip 字节不同 | conandata sha256 采用官方 archive URL 实际字节 c72ea6bc...，并经内容 diff 确认源码一致 |
| 3 | tests/CMakeLists.txt 报 gtest_discover_tests 未知 | 上游 CMakeLists 缺 include(GoogleTest)，CMakeDeps 配置包不自动加载 | 本地验证加最小补丁 include(GoogleTest)；该补丁仅用于本地验证不进配方 |
| 4 | flexray 模块测试不可构建 | v1.0.0 发布版 headers/ 不含 fmi3LsBusFlexRay.h（main/v1.1.0-beta.2 起才有） | 上游明确排除条件：104 个 flexray TEST 计 source_declared，不计通过；上游 CI 输入亦声明 "Available is can" |
| 5 | fmi3LsBus.h include "fmi3PlatformTypes.h" | 该头来自 fmi-standard 仓库，ohpcd registry 无此包 | 配方双源：官方 fmi-standard 固定提交 5365a49 引入，包随 include/ 安装 |
| 6 | conan-verify G1 缺 build()/apply_conandata_patches | header-only 模板无 build()，G1 静态检查要求 | build() 空实现仅调用 apply_conandata_patches（patches 为空，不伪造编译日志，R34） |
| 7 | HMDFS 大小写折叠污染（archives/l/libXext 两文件脏） | 已知平台案例冲突（libXext/libxext 双树） | 属其他库基线噪声，非本库改动，见 W3 基线隔离复验 |

## 源码修改

- tests/CMakeLists.txt：本地验证补 `include(GoogleTest)`（不进配方，配方无 patches）
- 无其他源码补丁（头文件原样安装）

## 依赖版本

- gtest/1.17.0.2（ohpcd registry 预编译包，仅头测试/消费者构建使用）
- fmi-standard headers @ 5365a49654d2f6e5b0bc7c75b5176b495dd72ac5（fmi3PlatformTypes.h 来源）

## 验证结果

```bash
# 上游测试（可实例化集合，OHOS 工具链）
ctest -N  -> Total Tests: 130
ctest     -> 100% tests passed, 0 failed out of 130

# 双口径统计
#   source_declared_total = 234（can 130 + flexray 104）
#   configured_executable_total = 130（v1.0.0 仅 can 模块头可实例化）
#   executed_passed_total = 130 -> 130/234 = 55.6%（全量口径）
#   可执行集合通过率 130/130 = 100%

# 鸿蒙专项测试
./fmi_3_ls_bus_ohos_test -> ALL HARMONYOS HEADER CHECKS PASSED (7 checks)

# 消费者用例（test_package/test.c）
conan create ... -> ALL CONSUMER CHECKS PASSED（8/8）
```
---

**编译结束**: 2026-09-22 22:29
**最终状态**: built
