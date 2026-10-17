# gmenuharness 0.1.6 适配笔记

## 编译环境
- 构建系统: CMake (>= 3.10)
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，conan 2.30）
- 状态: built（待真机预检）
- 上游: https://gitlab.com/ubports/development/core/gmenuharness, tag 0.1.6

## 背景

gmenuharness 是 Lomiri/UBports 的 GMenuModel 结构测试库（libgmenuharness）。
核心库 4 个源文件（MatchResult/MatchUtils/MenuItemMatcher/MenuMatcher），
仅依赖 glib-2.0/gio-2.0 与单个头文件 `lomiri/util/ResourcePtr.h`
（来自 liblomiri-api，header-only RAII 工具）。上游 CMake 对
`liblomiri-api` 做 REQUIRED pkg-config 探测，对 OHOS 无意义且制品仓未发布
该包，故配方移除该探测并在 `source()` 阶段 vendor 该头文件。

## 上游测试清点（来源：gmenuharness-0.1.6.tar.gz）

| # | 文件 | 用例 | 类型 | OHOS 可运行性 |
|---|------|------|------|---------------|
| 1 | tests/unit/TestMatchResult.cpp | SuccessFailAndMessage | gtest，无 Qt/DBus | 可运行 |
| 2 | tests/unit/TestMatchResult.cpp | MergeTwoFailed | gtest，无 Qt/DBus | 可运行 |
| 3 | tests/unit/TestMatchResult.cpp | MergeFailedIntoSuccess | gtest，无 Qt/DBus | 可运行 |
| 4 | tests/unit/TestMatchResult.cpp | CopyAssignment | gtest，无 Qt/DBus | 可运行 |
| 5 | tests/functional/FunctionalTests.cpp | ImportSimple | 需 Qt Core+DBus、libqtdbustest、dbus-test-runner、D-Bus session | 不可运行 |
| 6 | tests/functional/FunctionalTests.cpp | ImportDeeperMatchAll | 同上 | 不可运行 |

合计 6 个 gtest 用例。`test_package` 在 test_package 阶段直编直跑前 4 个
（`test_upstream_unit`，hmbs 只从该阶段 stdout 采集
`HMBS_UPSTREAM_TEST_RESULT`），框架实测 discovered=4/executed=4/passed=4；
后 2 个因缺少 Qt DBus + libqtdbustest + D-Bus session 栈而不在执行集内，
在 MANIFEST/notes 及 marker reason 中如实声明。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pkg_check_modules(LOMIRI_API ... REQUIRED)` 在 OHOS 找不到 `liblomiri-api.pc` | 该包是 Ubuntu/UBports 特有，未发布到 ohpcd 制品仓 | 补丁 0001 移除两处探测；`source()` 将 lomiri-api 0.3.2 的 `ResourcePtr.h`（LGPL-3.0，同作者）vendor 到 `include/lomiri/util/`，`MatchUtils.cpp` 无需改动 |
| 2 | `enable_tests=ON` 要求 Qt/GMock/libqtdbustest | OHOS 无该测试栈 | `-Denable_tests=OFF -DWerror=OFF` 构建主库；单元测试另行用 `test_requires("gtest/1.17.0")` 直编直跑 |
| 3 | `-Werror` 在新版 clang 下可能将警告判错 | 上游老代码警告级别高 | `-DWerror=OFF` |

## 验证结果

待 hmbs 真机预检（conan create，含上游 4 个单元测试与 test_package 2 个消费者测试）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（glib 依赖 + vendored 头 + 直跑上游单元测试 + HMBS 标记） |
| conandata.yml | 官方 GitLab 源 + sha256 + 补丁声明 |
| patches/0001-remove-lomiri-api-dependency.patch | 移除 liblomiri-api 探测（无平台宏，R8 合规） |
| patches/vendored/lomiri/util/ResourcePtr.h | vendored 头文件（LGPL-3.0，版权保留） |
| test_package/ | CMake 无关的直编消费者测试（MatchResult + MenuItemMatcher 真实 API） |
| manifest.yaml | 版本元数据 |
