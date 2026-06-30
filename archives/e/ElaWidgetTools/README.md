# ElaWidgetTools

## 简介
ElaWidgetTools 是一个基于 Qt 的 Fluent Design 风格组件库，为 Qt Widget 应用程序提供现代 UI 组件。

## 功能概述
- 提供 Fluent Design 风格的 Qt Widget 组件
- 包含窗口、导航栏、按钮、卡片、对话框等丰富组件
- 支持主题切换（亮色/暗色）
- 支持 Qt5 和 Qt6
- 提供静态库和动态库两种构建模式

## OHOS 适配
### 适配要点
1. **Qt5 依赖**：ElaWidgetTools 依赖 Qt5 Widgets 模块，HarmonyOS 上无预编译 Qt5 包，需从源码编译 Qt5 qtbase 5.15.2
2. **Qt5 编译修复**：
   - musl libc 不支持 `pthread_cancel`，需在 `qthread_unix.cpp` 中用 `#if !defined(__OHOS__)` 保护相关代码
   - `socklen_t` 在 HarmonyOS 上为 `unsigned int`，需修改 `qplatformdefs.h` 中的 `QT_SOCKLEN_T` 定义
   - `qt_functions.prf` 中需添加 `HarmonyOS` 到支持的操作系统列表（`QMAKE_HOST.os` 检测）
3. **Stripped 二进制问题**：HarmonyOS 上 stripped 的 ELF 二进制文件无法执行，需使用非 stripped 版本的 Qt5 工具（moc/rcc/uic）和库（libQt5Core.so 等）
4. **CMake 配置**：
   - 修改 `QT_SDK_DIR` 为本地 Qt5 安装路径
   - 修改 `CMAKE_INSTALL_PREFIX` 为可覆盖（原代码使用 FORCE 硬编码）
   - 添加 `-stdlib=libc++` 编译和链接标志
5. **libc++ 标准库**：Qt5 使用 libc++（非 libstdc++），ElaWidgetTools 编译时需保持一致

### 已知问题
- 无重大已知问题

## 依赖
### 编译依赖
- Qt5 qtbase 5.15.2（含 Core、Gui、Widgets、WidgetsPrivate 模块）

### 运行依赖
- Qt5 运行时库（libQt5Core.so、libQt5Gui.so、libQt5Widgets.so）

## 参考
- 源码仓库：https://github.com/Liniyous/ElaWidgetTools
- Qt5 下载：https://download.qt.io/archive/qt/5.15/5.15.2/single/
