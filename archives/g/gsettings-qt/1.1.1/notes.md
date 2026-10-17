# gsettings-qt 1.1.1 适配笔记（HarmonyOS PC / arm64）

## 编译环境
- 构建系统: **CMake**（上游 `CMakeLists.txt`，project(gsettings-qt VERSION 1.1.1 LANGUAGES CXX)）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: **built**（conan create 通过 + 上游测试通过 + conan-verify 通过）
- 构建方式: `conan create archives/g/gsettings-qt/1.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="gsettings-qt/*"`（与 CI `ci/conan/build_and_test.sh` 同参数）

## 上游测试清点（R51 申报表）

| ctest 用例 | 上游文件 | 用例数（实测） | 结果 |
|---|---|---|---|
| `cpptest` | `tests/cpptest.cpp`（QtTest） | 7（initTestCase + 5 测试槽 + cleanupTestCase） | 全部通过 |
| `qmltest` | `tests/test.cpp` + `tests/tst_GSettings.qml`（QtQuickTest） | 9（initTestCase + 7 QML 测试函数 + cleanupTestCase） | 全部通过 |

合计 **16 项通过 / 0 失败 / 0 跳过**；日志: `reports/upstream-tests.log`。
测试入口（上游）: `tests/CMakeLists.txt` 的 `add_test(NAME cpptest ...)` / `add_test(NAME qmltest ...)`，
运行时环境由上游 `set_tests_properties` 指定（`GSETTINGS_SCHEMA_DIR`、`GSETTINGS_BACKEND=memory`、`QT_QPA_PLATFORM=minimal`、`QML2_IMPORT_PATH`）。

## 编译步骤（关键命令）

```bash
# 1) 依赖为制品仓已发布包，无 --build=missing 兜底需求（R36）
conan create archives/g/gsettings-qt/1.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="gsettings-qt/*"
# 2) 配方内：cmake configure(-DENABLE_QT6=ON -DBUILD_TESTING=ON) → build → 签名 → ctest → install → package 内再签名
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `qmltest` 失败：`Type TestCase unavailable` / `module "QtQuick.Window" is not installed` | 上游 `set_tests_properties` 把 `QML2_IMPORT_PATH` 固定为构建树，覆盖了环境变量；QtTest/TestCase.qml 依赖 QtQuick.Window 等模块，而 conan 依赖包的 QML 模块在 `qtdeclarative/qml/` 下，未被扫描 | 在 `generate()` 注入 `QML_IMPORT_PATH`（Qt6 同时读取该变量，且不被测试属性覆盖）指向 `qtdeclarative`/`qtbase`/`qtshadertools` 包的 `qml/` 目录；**未修改上游文件** |
| 2 | `package_info()` 报错：`The direct dependency 'cmake-extras' is not used by any (cpp_info/components).requires` | cmake-extras 是纯 CMake 模块数据包，作为 host requires 会强制其进入消费者依赖链 | 改为 `self.tool_requires("cmake-extras/1.9")`，`generate()` 内用 `self.dependencies.build[...]` 取包目录 |
| 3 | test_package 编译失败：`'QGSettings' file not found` | 上游把转发头文件 `QGSettings` 与 `qgsettings.h` 装到 `include/<triplet>/qt6/QGSettings/`，include 目录必须是该目录本身（其 .pc 的 Cflags 亦如此），初始实现取了父目录 | 修正 `cpp_info.includedirs`（配方）与 test_package 的 include 探测：定位 `qgsettings.h` 所在目录 |

（问题 1/2/3 均在本地 `conan create` 复现→修复→重跑验证，逐次日志见仓库外分析目录 `logs/36-39`。）

## 源码修改

**无补丁**（`patches/` 为空）：三处问题全部通过配方侧（构建环境注入 / 依赖声明 / 安装布局识别）解决，未改动上游源码。

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| qtbase | 6.11.1 | Qt6::Core（公开头 + 链接） |
| qtdeclarative | 6.11.1 | Qt6::Qml（QML 插件）、Qt6::QuickTest（上游 qmltest）、`bin/qmlplugindump`（configure 阶段必需） |
| glib | 2.88.3 | gio-2.0（`gio/gio.h`、`.pc Requires: gio-2.0`）、`bin/glib-compile-schemas`（测试 schema） |
| pkgconf（tool） | 3.0.6 | `find_package(PkgConfig REQUIRED)`，提供 `pkg-config` 别名 |
| cmake-extras（tool） | 1.9 | `QmlPlugins.cmake` / `add_qmlplugin` |

Qt6 版本必须为 **6.11.1**：`qtdeclarative/6.11.1` 以精确版本依赖 `qtbase/6.11.1`（制品仓另有 6.11.1.2，混用会产生 Version conflict）。

## 验证结果

```bash
# 制品仓依赖可消费（W0）
conan download qtbase/6.11.1 qtdeclarative/6.11.1 glib/2.88.3 cmake-extras/1.9 pkgconf/3.0.6 -r=ohpcd --only-recipe   # EXIT=0
# 本地构建 + 上游测试 + test_package（W3，CI 同参数）
conan create archives/g/gsettings-qt/1.1.1 -pr:h=... -pr:b=... --build=missing --build="gsettings-qt/*"   # EXIT=0
#   上游 ctest: 100% tests passed, 0 tests failed out of 2
#   test_package: 13 项断言全部 PASS（OK: 0 failure(s)）
# 配方门禁（conan-verify: G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify gsettings-qt 1.1.1   # PASS
```

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libgsettings-qt6.so.1.0.0`（+ `.so.1`、`.so`） | 库本体（SOVERSION 1，已签名） |
| `include/aarch64-linux-ohos/qt6/QGSettings/{qgsettings.h,QGSettings}` | 公开头文件与转发头 |
| `lib/pkgconfig/gsettings-qt6.pc` | pkg-config 元数据（`Requires: gio-2.0`） |
| `lib/qt6/qml/GSettings/{qmldir,libGSettingsQmlPlugin.so,plugins.qmltypes}` | QML 模块 GSettings 1.1 |

## 注意事项

- 纯库包（无命令行工具）→ **不需要** `commands.json`（R38 仅 CLI 工具适用）。
- `find_program(qmlplugindump REQUIRED)` 属 configure 阶段硬依赖；若后续依赖包裁剪 `bin/`，configure 会直接失败（QmlPluginsConfig.cmake 抛 `FATAL_ERROR "Could not locate qmlplugindump."`）。
- OHOS 的 `.so` 与测试可执行文件均需签名；配方在 `build()`（测试前）与 `package()` 各签名一次，重复签名会先移除旧 `.codesign` 段。
- `plugins.qmltypes` 由已废弃的 `qmlplugindump` 生成（构建时有 deprecation 警告），属上游既有行为，未改动。

### 对话 #1 — 首次适配（2026-09-15）

- **目标**：gsettings-qt 1.1.1 本地完成 构建 → 上游测试 → test_package → conan create → conan-verify → finish（停在 LOCAL_AUDIT_PASS，不 commit/push）。
- **前置**：`conan download --only-recipe` 验证 5 个直接依赖 + 11 个传递依赖全部可消费（EXIT=0）。
- **执行链**：`init-build` → `lang-preflight`(cpp) → `conan-init`（模板误判为 autotools，已重写为 CMake 配方）→ `conan create` 迭代 4 次 → `conan-verify` PASS → `finish built`。
- **失败与修复**：
  1. `qmltest`：`Type TestCase unavailable` / `module "QtQuick.Window" is not installed`
     → 根因：上游测试属性覆盖 `QML2_IMPORT_PATH`；修复：注入 `QML_IMPORT_PATH` 指向依赖包 `qml/`。
  2. `package_info()`：`direct dependency 'cmake-extras' is not used by any (cpp_info/components).requires`
     → 修复：cmake-extras 改 `tool_requires`，用 `self.dependencies.build[...]` 取路径。
  3. test_package：`'QGSettings' file not found`
     → 根因：转发头文件 `QGSettings` 与 `qgsettings.h` 同目录，include 目录取错；修复：以 `qgsettings.h` 所在目录为 include 目录。
- **结果**：上游 16 项用例全通过；test_package 13 项断言全通过；`conan-verify` PASS；W3 本地 CI 模拟 PASS。
- **产物**：`libgsettings-qt6.so.1.0.0`、`gsettings-qt6.pc`、QML 模块 `GSettings 1.1`、公开头 `QGSettings`。
- **未做（按要求停止）**：commit / push / Issue / PR / 上传制品 / 远端 Review。
---

**编译结束**: 2026-09-15 16:30
**最终状态**: built
