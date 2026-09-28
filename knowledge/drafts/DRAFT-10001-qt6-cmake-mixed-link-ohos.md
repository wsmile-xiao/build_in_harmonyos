# DRAFT-10001: Qt6 CMake 应用 + 非 Qt 第三方库裸 SET() 混链的 OHOS Conan 适配模式

- **来源**：qastools 1.4.0 适配（2026-09-19）
- **关联 PR**：#11414【知识库扩展】feat(qastools): 1.4.0 适配 HarmonyOS PC
- **前置条目**：E438（单 qtbase 包消费的标准做法），本条目是其多包 + 混链扩展

## 问题（一类）

Qt6 CMake 应用，同时链接非 Qt 第三方库（alsa-lib、libudev 等），且上游用裸
`SET()` / `TARGET_LINK_LIBRARIES( ... ${FOO_LIBRARIES} )` 管理依赖，目标 OHOS aarch64。
五个固定卡点：

1. **Qt 组件跨包**：`find_package(Qt6 REQUIRED COMPONENTS X)`，X 属于独立包（Svg/Tools…）时找不到；
2. **LinguistTools 缺失**：制品仓 qtbase 变体均不构建 lupdate/lrelease；
3. **头目录不向子目录传递**：顶层 `INCLUDE_DIRECTORIES` 不进子目录作用域；
4. **子目录 `SET()` 覆盖顶层 cache 变量**：`-DFOO_LIBRARIES=<绝对路径>` 被 `SET(FOO_LIBRARIES foo)` 覆盖；
5. **musl 短头链**：glibc 下间接包含的 STL 头变显式缺失。

## 证据（真实日志）

| 卡点 | 报错原文（qastools 本地构建日志） |
| --- | --- |
| 2 | `Failed to find required Qt component "LinguistTools"` |
| 1 | `Could NOT find Qt6Svg (missing: Qt6Svg_DIR)` |
| 3 | `fatal error: 'libudev.h' file not found` |
| 4 | `ld.lld: error: unable to find library -ludev` / `undefined symbol: udev_new` |
| 5 | `states_db.cpp:64: error: implicit instantiation of undefined template 'std::basic_ostringstream<char>'` |

修复后 `conan create archives/q/qastools/1.4.0 ... --build=missing` 全通过，
test_package TP-001..006 全 PASS（日志 `.ci_logs/target_qastools.log`）。

## 解法（按卡点）

1. conanfile `generate()`：每个 Qt 包目录拼进 `CMAKE_PREFIX_PATH` + `Qt6<Comp>_DIR` 缓存变量；
2. `FIND_PACKAGE(Qt6 QUIET COMPONENTS LinguistTools)` 守卫，缺失跳过 i18n 子目录；
3. 顶层 `PROJECT()` 后注入 `INCLUDE_DIRECTORIES(${X_INCLUDE_DIRS})`（conanfile 传绝对路径）；
4. `FOO_LIBRARIES_CACHE` 后缀变量 + 子目录 `IF(DEFINED ..._CACHE)` 守卫；
5. 报错处显式 `#include`（`<sstream>` 等）。

## 适用范围

- kde/qt 应用系、alsa+udev 混链音频 GUI、任何裸 `SET()` 管理依赖路径的 CMake 项目。

## 反模式

- ✗ 裸 `SET(UDEV_LIBRARIES udev)` 直接上 Conan（静态库 + HMDFS 无搜索路径必挂）；
- ✗ 期望 CMakeDeps 导入 target 自动替换上游裸 `SET()` 变量（不会）；
- ✗ 把 LinguistTools 当必选组件硬等制品仓补建（翻译运行时加载时应降级跳过）。
