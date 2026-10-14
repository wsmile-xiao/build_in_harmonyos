# notes.md — kirigami-gallery 26.04.0 适配笔记

## 1. 软件概述

- **上游**: https://invent.kde.org/graphics/kirigami-gallery （KDE Release Service 26.04.0）
- **源码**: https://download.kde.org/stable/release-service/26.04.0/src/kirigami-gallery-26.04.0.tar.xz
  - sha256 `f85b0ac55c7912b4969d6a30facb87675084e36bc994b1142603e6ea6b9f3386`
- **语言/构建**: C++17（main.cpp、InfoData.cpp）+ QML（56 个文件经 resources.qrc 内嵌）；CMake + ECM
- **产物**: GUI 可执行 `kirigami2gallery`（application，R38 已声明 commands.json）

## 2. W0 依赖发布检查（R35 口径，conan download 实测）

| 依赖 | 版本 | 实测 |
|---|---|---|
| qtbase | 6.11.1 | ✅ 已发布 |
| qtdeclarative | 6.11.1 | ✅ 已发布 |
| qtsvg | 6.11.1 | ✅ 已发布 |
| qtshadertools | 6.11.1 | ✅ 已发布 |
| kirigami | 6.26.0 | ✅ 已发布 |
| kitemmodels | **6.18.0.1** | ✅ 已发布（6.26.0 不存在，404 实测） |
| ecm（tool） | 6.26.0 | ✅ 已发布 |

上游要求：Qt ≥ 6.0.0、KF6 Kirigami/ItemModels ≥ 6.12.0（CMakeLists.txt）→ 全满足。
kitemmodels/6.18.0.1 只依赖 qtbase+qtdeclarative 6.11.1，无版本冲突。

## 3. lang-preflight 误判记录（重要，R47 复核）

`lang-preflight` 判定 `mixed → env_unsupported`，**经人工复核为工具误判**，证据链：

1. 工具按**文件名**递归匹配 manifest（lang_detect.py `_manifest_scan` 按 basename 匹配，
   gradle 检查优先于 CMake）→ 命中 `src/android/build.gradle` → 误判 `java`。
2. `src/android/build.gradle` 是 Qt/KDE 应用的 **Android APK 打包辅助文件**
   （`ecm_add_android_apk` 仅 `if (ANDROID)` 使用，桌面/通用平台路径完全不用它），
   不是项目构建系统；项目唯一构建系统是**根级 CMakeLists.txt**（cmake_minimum_required 3.16 +
   project(kirigami2gallery)）。
3. 源码统计：cpp 2 文件（main.cpp/InfoData.cpp）+ QML 56 + bash 1（辅助脚本不计主体）→ 主体 100% cpp。
4. 边界规则"辅助脚本不算主体"适用：android/ 子目录是打包辅助产物目录。

**处置**：不删除源码文件迎合检测器（避免伪造证据）；如实记录误判分析于本笔记，
任务继续执行（任务指派明确为 C++/Qt 库适配）；终态 result 以真实状态覆盖上报（--force），
该模式已沉淀知识库草稿（见 knowledge/drafts/）。

## 4. 构建要点与决策

- **KF_SKIP_PO_PROCESSING=ON**: 跳过 `ecm_install_poqm_files_as_qm(poqm)`。
  依据：ECMPoQmTools.cmake 第 88/134 行（extra-cmake-modules 6.26.0 源码）：
  `option(KF_SKIP_PO_PROCESSING ...)` + `if (KF_SKIP_PO_PROCESSING) return()`。
  否则需 find_package(Qt6 LinguistTools)（qttools 包）。与 kirigami-addons/1.13.0 先例一致。
- **KF_IGNORE_PLATFORM_CHECK=TRUE**: KF6 cmake 平台守卫不认识 OHOS。
- **ENABLE_QML_PROFILING=OFF** + BUILD_TESTING=OFF：上游无测试（见 §5），QML profiling 无用。
- **Qt 私有模块**: 无（源码未用 Qt6::GuiPrivate，与 kirigami 6.26 库本身不同）。
- **无平台宏补丁**: 当前零补丁。所有 OHOS 差异由 conan 侧解决（R8/PF5 口径）。
- **无 R26 风险**: application 产物，不安装共享库；Qt/KF6 依赖链全部 conan 管理。

## 5. 上游测试三步法（R51）

1. **清点**：`find . -iname "*test*" -o -iname "autotests"` → 空；
   `grep -rn "add_test|enable_testing|ECMAddTests" --include=CMakeLists.txt` → 空。
   **上游无测试套件**（demo 应用）。
2. **运行**：无官方测试可运行（上一步证据）。
3. **补齐**：test_package/test_runner.c 消费者端到端测试——fork+exec 被测包二进制
   （QT_QPA_PLATFORM=offscreen + QML2_IMPORT_PATH），验证完整 QML 栈真实加载：
   main.cpp 的 `engine.rootObjects().isEmpty() → return -1` 是天然失败信号，
   存活 8 秒 = QML UI 加载成功。详见 test_package/MANIFEST.yml。

## 6. 配方消费模式（Qt6/KF6 应用）

复用 kirigami-addons/1.13.0 验证过的模式：
- `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入 `conan_cmakedeps_paths.cmake`
  （CMAKE_PREFIX_PATH/LibraryPath/IncludePath/ModulePath 汇聚全部依赖包目录）
- `ECM_MODULE_PATH` 指向 ecm 包 share/ECM/{modules,find-modules,kde-modules}
- `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 指向 qtdeclarative/qtsvg/qtshadertools
- 宿主工具环境（qmlcachegen/qsb）：LD_LIBRARY_PATH 补依赖包 lib+bin + 干净的
  /system/lib64{,/platformsdk,/ndk}（OHOS shell LD_LIBRARY_PATH 有空白填充脏值）+
  QT_PLUGIN_PATH 双布局 + QT_QPA_PLATFORM=offscreen

## 6.5 test_package 调试记录（conan create 迭代）

首次 conan create 卡在 test()：`module "basic" is not installed`。三步定位：
1. QML_IMPORT_TRACE 确认库路径/import path 全就位（QtQuick/QtQml 加载成功）；
2. 用 qtdec 包自带 qml 工具隔离最小用例：`import QtQuick.Controls.Basic`（显式）成功；
   `QT_QUICK_CONTROLS_STYLE=basic`（环境变量）失败；
3. 对照实验：`QT_QUICK_CONTROLS_STYLE=Basic`（大写 B）成功。

**根因**：本机 Qt 6.11 OHOS 构建的 QQC2 环境变量样式选择区分大小写，样式值必须与
QtQuick/Controls/Basic 模块目录名一致（"Basic"）。上游 main.cpp 只判断该变量是否为空
（非空则不设 org.kde.desktop），与值无关 → test_package 用 "Basic" 即可。

另：QFontDatabase 字体目录告警与 headless offscreen 环境相符，不阻断。

## 7. 时间线

- 2026-09-29 18:0x W0/W1 完成，分支 feat/kirigami-gallery-26.04.0 建立
- 2026-09-29 18:1x conan-init + 配方手写完成，进入 conan create 迭代
---

**编译结束**: 2026-09-30 10:29
**最终状态**: built
