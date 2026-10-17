# DRAFT-bambootracker-qt6-executable-conan — 知识图谱草稿（未登记 E###）

> 来源：BambooTracker 0.6.5 适配（R14–R21），路径 B 知识沉淀候选。
> 本文件为草稿，不修改任何正式知识文件；登记前需复查。

## topic

Qt6 纯可执行 GUI 包的 Conan 配方与 test_package 消费者模式（含 CMake 4.x / Qt6 组件供给）。

## error_signature

- `Library '<pkg>' not found in package`（CMakeDeps 因 package_info 声明不存在的 cpp_info.libs 生成指向缺失库的 target）
- `Error loading shared library ... libQt6Core.so.6`（lrelease/Qt 工具运行期找不到 qtbase 库）
- `Unable to locate either Qt5 or Qt6`（CMAKE_PREFIX_PATH 未供给 Qt 前缀）
- `cmake_minimum_required` ... CMake 4.x 已移除 <3.5 支持（子模块声明旧最低版本）

## root_cause

1. Qt6 GUI **纯可执行包**（无 lib/ 产物）若在 `package_info()` 声明 `cpp_info.libs = ["<pkg>"]`，CMakeDeps 会生成指向缺失库的 target，导致 test_package 的 `find_package`/链接失败（"Library not found"）。
2. Qt6Config 组件搜索受 PATHS 限定在 qtbase 前缀，LinguistTools(qttools)/Core5Compat(qt5compat) 需显式 `Qt6LinguistTools_DIR` / `Qt6Core5Compat_DIR` 供给，否则 configure 无法解析组件。
3. CMake 4.x 已移除 `cmake_minimum_required(VERSION < 3.5)` 支持；子模块（如 emu2149）声明 `VERSION 2.8` 时 configure 失败，需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
4. Qt 工具（lrelease）运行期需加载 qtbase 动态库，build() 需供给 LD_LIBRARY_PATH。

## solution

1. `package_info()` **不声明虚假 cpp_info.libs**（纯可执行包留空/仅 bindirs）。
2. test_package 改为**运行安装的二进制** offscreen smoke（`test.sh`，`QT_QPA_PLATFORM=offscreen`，Qt 初始化成功 rc=124 即通过），而非链接不存在的库。
3. `generate()` 用 `tc.cache_variables` 显式供给：
   - `CMAKE_PREFIX_PATH`（qtbase/qt5compat/qttools/alsa 包目录）
   - `Qt6LinguistTools_DIR`（qttools 组件目录）
   - `Qt6Core5Compat_DIR`（qt5compat 组件目录）
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`
   - `WARNINGS_ARE_ERRORS=OFF`（GUI 上游默认 -Werror 时按需）
4. `build()` 用 `Environment` 供给 qtbase `LD_LIBRARY_PATH` 供 lrelease 运行期加载。

## scope

- 适用：Qt6/Qt5 GUI **纯可执行包**（无库产物）的 Conan 2 配方与 test_package 消费者适配；CMake 4.x 工具链；OHOS aarch64 无头（offscreen）测试环境。
- 边界：库型包（有 lib/ 产物）仍需正常声明 cpp_info.libs；若上游提供可链接测试程序可用 CMake 消费者，否则用二进制 smoke。

## 验证（BambooTracker 0.6.5 实证）

- `conan create` 干净构建 G2 PASS（Conan G0-G4 全 PASS）。
- test_package 消费者：`[test] BambooTracker offscreen init OK (rc=124)`（offscreen smoke 通过）。
- W3 本地 CI：Pass rate 100.0% (1/1)，All packages built and tested successfully。
- finish 官方流程真实退出码 0（本地验证）。
- 报告/日志：`archives/b/bambootracker/0.6.5/reports/conan-verify-report.md`（Verdict PASS）、`reports/conan-create.log`、`reports/w3-local-ci.log`。

## 查重差异

- E225（CMakeToolchain source-side preset / test_package 临时布局）：聚焦 preset/布局，未覆盖"纯可执行包勿声明虚假 cpp_info.libs + 运行二进制 smoke 消费者"。
- E298（Conan test_package 显式运行环境/VirtualRunEnv）：聚焦运行环境注入，未覆盖可执行包消费者模式与 Qt6 组件显式供给。
- E216/E221（共享库加载/权限）：聚焦运行期 .so 加载，未覆盖配方/消费者层面。
- 本文档核心增量：**Qt6 纯可执行包 Conan 配方语义（cpp_info.libs 正确留空）+ test_package 二进制 offscreen smoke 消费者 + Qt6 组件显式 DIR 供给**。

## 适用条件与维护

- 登记后更新 `knowledge/graph/index.tsv` 与 `knowledge/doc/`（如需）。
- 本草稿 `id` 为 `DRAFT-bambootracker-qt6-executable-conan`，未创建正式 `E###` 条目，未修改任何既有知识文件。
