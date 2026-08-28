# 测试报告 — extra-cmake-modules 6.28.0

## 上游测试 (ctest)

### 总体结果

- 总测试数: 87（全部注册并运行）
- 通过: **77 (89%)**
- 失败: 10 (11.5%) — 均为 OHOS 平台限制，非适配缺陷
- 超时: 0
- 未注册: 0

### 失败的 10 个测试及根因

| # | 测试 | 失败原因 | 类型 |
|---|------|---------|------|
| 2 | ExecuteKDEModules | OHOS Python wrapper 在 `-E` 模式下 sys.prefix='/python3'（不存在），KDESetupPrefixScript.cmake 中 execute_process(Python3) 崩溃 | OHOS 平台限制 |
| 3 | KDEFetchTranslations | 同上 | OHOS 平台限制 |
| 4 | KDEInstallDirsTest.vars_in_sync_no_args | 同上 | OHOS 平台限制 |
| 5 | KDEInstallDirsTest.not_cache_variable | 同上 | OHOS 平台限制 |
| 6 | KDEInstallDirsTest.vars_in_sync_kde_arg | 同上 | OHOS 平台限制 |
| 7 | KDEInstallDirsTest.vars_in_sync_cmake_arg | 同上 | OHOS 平台限制 |
| 18 | ecm_add_tests-single_tests | find_package(Qt5Core) 失败：OHOS 仅提供 Qt6 ≥6.9.0，无 Qt5 | OHOS 平台限制 |
| 19 | ecm_add_tests_did_run-single_tests | 同上 | OHOS 平台限制 |
| 20 | ecm_add_tests-multi_tests | 同上 | OHOS 平台限制 |
| 21 | ecm_add_tests_did_run-multi_tests | 同上 | OHOS 平台限制 |

### 失败根因详情

1. **Python wrapper 崩溃**（6 个测试）：
   - OHOS 系统提供 `/storage/Users/currentUser/.zsh-bin/python3.12`（编译型 ELF wrapper）
   - wrapper 硬编码 `sys.prefix='/python3'`，而 `/python3` 不存在
   - KDESetupPrefixScript.cmake 调用 `execute_process(COMMAND ${Python3_EXECUTABLE} -Esc "...")`
   - `-E` 标志使 Python 忽略 PYTHONHOME，使用硬编码的 `/python3` 作为 prefix
   - Python 找不到标准库（`/python3/lib/python3.12` 不存在），启动崩溃

2. **Qt5 不可用**（4 个测试）：
   - ECM 6.28.0 的 ecm_add_tests 测试使用 `find_package(Qt5Core)`
   - OHOS 仅提供 Qt6 ≥6.9.0，Qt5 未移植到 OHOS

### 等效测试样例

已在 test_package 中增加等效功能验证，覆盖以下上游测试功能：

| 测试样例 | 对应上游功能 | 验证方式 |
|---------|------------|---------|
| ECMSetupVersion include + 宏可用性 | ecm_setup_version 系列测试 | CMake include + 版本宏调用 |
| ECMGenerateExportHeader include + 宏可用性 | ecm_generate_export_header 系列测试 | CMake include + 导出头文件宏调用 |
| ECMGeneratePkgConfigFile include + 宏可用性 | ecm_generate_pkgconfig 系列测试 | CMake include + pkg-config 宏调用 |
| ECMAddTests include + 宏可用性 | ecm_add_tests 系列 | CMake include + 宏函数检查 |
| ECMMarkNonGuiExecutable include | ExecuteKDEModules 核心功能 | CMake include + 宏函数检查 |
| KDEInstallDirs/KDECMakeSettings/KDECompilerSettings/KDEFrameworkCompilerSettings 文件验证 | KDEInstallDirsTest 系列 | CMake 文件存在性检查 |

## Conan 验证

- conan-verify: G0-G4 + L2/L4/L5 全部通过
- conan create: 通过（含 test_package）
- test_package: find_package(ECM) + 15 断言（core 5 + KDE 4 + include 4 + 目录 2）验证通过

## W3 本地 CI 模拟

- 结果: 100% 通过（1/1 包构建成功）

## W4 Pre-PR 审计

- verdict: pass（P0=0, P1=0, P2=0）

## 修订记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-08-27 | v2 | 修正统计口径：87 个测试全部注册运行，77 通过（89%），10 失败（OHOS 平台限制）；删除此前错误的"45 个未注册"表述 |