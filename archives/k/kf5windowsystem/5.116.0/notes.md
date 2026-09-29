# kf5windowsystem 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (KDE Extra CMake Modules)
- 编译日期: 2026-09-28
- 编译器: clang (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```
conan create archives/k/kf5windowsystem/5.116.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 包定位

`kwindowsystem` 是 KDE 的窗口系统抽象层，产出 `libKF5WindowSystem.so`。
KF5 分支（5.116.0）面向 Qt5，是已上架的 KF6 配方
（`archives/k/kwindowsystem/6.14.0|6.18.0|6.26.0`）的 Qt5 对应物。

平台后端是 QPlugin。与 KF6 不同，KF5 没有 `KWINDOWSYSTEM_X11` /
`KWINDOWSYSTEM_WAYLAND` 选项：顶层 CMakeLists.txt 自己探测 X11，并由
`X11_FOUND` 推导出 `KWINDOWSYSTEM_HAVE_X11`。OHOS 没有 X11/Wayland 栈，
因此用 `CMAKE_DISABLE_FIND_PACKAGE_X11=TRUE` 关掉；库会退回到**始终参与编译**
的 dummy 后端（`src/kwindoweffects_dummy.cpp` + `KWindowSystemPrivateDummy`），
与 KF6 配方两个后端全关时的最终状态一致。

## OHOS 适配点

| 适配 | 说明 |
|------|------|
| `QT_MAJOR_VERSION=5` | 工程调用 `find_package(Qt${QT_MAJOR_VERSION}Gui ...)`，必须解析到 Qt5（qt5-qtbase/5.15.2.2） |
| `KF_IGNORE_PLATFORM_CHECK=TRUE` | OHOS 不在 KDE 平台清单里，绕过平台检测 |
| `CMAKE_DISABLE_FIND_PACKAGE_X11=TRUE` | OHOS 无 X11 栈：顶层与 autotests/ 两处 `find_package(X11)` 都跳过，`X11_FOUND` 为假 → 走 dummy 后端，`src/platforms/xcb` 不编译 |
| 补丁 0001 去掉 `ecm_install_po_files_as_qm(poqm)` | 该宏会 `find_package(Qt5LinguistTools CONFIG REQUIRED)`，而 Qt5LinguistTools 未发布到 ohpcd；翻译目录对 OHOS baseline 非必需（与 KF6 kwindowsystem 配方同样的处理） |
| `ecm` 为 tool_requires | `ecm/6.26.0` 满足 `find_package(ECM 5.116.0 NO_MODULE)`（最小版本语义，与 ki18n5/5.116.0 相同） |
| `CMakeDeps` 的 `cmake_file_name "Qt5"` | qt5-qtbase 只发每模块 cmake config，没有聚合的 Qt5Config；消费方 `find_package(Qt5 COMPONENTS ...)` 需要一个（ki18n5 模式） |
| `CMAKE_AUTOMOC_EXECUTABLE` / `CMAKE_AUTORCC_EXECUTABLE` | 指向 qt5-qtbase 的 `bin/moc`、`bin/rcc`（CMakeDeps 不导出 Qt5::moc/rcc） |
| SONAME | HarmonyOS 未映射到 Linux CMake 平台，`CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG` 未定义会让产物 .so 缺 DT_SONAME（CI L5 门禁）；设 soname flag + `CMAKE_PLATFORM_NO_VERSIONED_SONAME`（expat / ki18n5 验证过的写法） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ecm_install_po_files_as_qm(poqm)` 报找不到 Qt5LinguistTools | 上游 CMakeLists.txt 无条件调用，Qt5LinguistTools 未发布 | 补丁 0001 注释掉该行 |
| 2 | `ecm_create_qm_loader()` 找不到 ECMQmLoader.cpp.in | 该宏配置 `${ECM_MODULE_DIR}/ECMQmLoader.cpp.in` | generate() 里除 ECM_DIR / ECM_MODULE_PATH 外同时导出 `ECM_MODULE_DIR` |
| 3 | Qt5::Core 引用不存在的 mkspecs 路径 | `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码 `<pkg>/../b/mkspecs/linux-clang` | ki18n5 验证过的 `_prepare_qt_mkspec_compat`：把包内 mkspecs 拷到预期位置 |
| 4 | 消费方 `find_package(KF5WindowSystem)` 后 Qt5::Gui/Widgets 未定义 | `KF5WindowSystemConfig.cmake` 里 `find_dependency(Qt5Gui 5.15.2)` / `find_dependency(Qt5Widgets 5.15.2)` | test_package 先 `find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets)`（CMakeDeps 聚合 Qt5Config 提供这些组件） |
| 5 | 直接跑 KWindowSystem 时无平台插件 | `pluginwrapper.cpp` 的 `loadPlugin()` 在没有 QGuiApplication 时直接返回 nullptr | 消费测试在 offscreen QPA 下构造 QGuiApplication（`QT_QPA_PLATFORM=offscreen` + `QT_QPA_PLATFORM_PLUGIN_PATH`），随后观测到 dummy 后端 |
| 6 | autotests/ 里无条件 `find_package(XCB COMPONENTS XCB ICCCM KEYSYMS)` | 该调用不是 REQUIRED | 无需处理：ECM 的 FindXCB.cmake 只用 `find_package_handle_standard_args`，找不到就是静默 not-found，不会 FATAL_ERROR |

## 上游测试清点（BUILD_TESTING=ON，X11 关闭）

上游源码里声明的测试目标共 **22 个**（12 个 X11 门控单元测试 + 3 个 X11 门控
可执行测试 + 1 个无条件 wayland 平台测试 + 1 个 wayland helper +
`tests/` 下 5 个（2 个无条件交互式演示 + 3 个 X11 门控））；OHOS 特性集下
CTest 只注册其中 **1 个**。按评审脚本的朴素文本扫描口径
（`grep -rE "add_executable\(|ecm_mark_as_test\("`）则是 **6** 处声明
（`autotests/` 2 + `autotests/helper/` 2 + `tests/` 2）。

- 实际注册 **1 项 CTest**：`kwindowsystemplatformwaylandtest`
  （autotests/CMakeLists.txt 末尾无条件 `ecm_add_test(kwindowsystem_platform_wayland_test.cpp)`）。
  它的 `initTestCase()` 用 `QStandardPaths::findExecutable("weston")` 找 weston，
  CI 里 PATH 上没有 weston → `QProcess::waitForStarted()` 失败 → `QSKIP`，
  ctest 记为 Passed。
- **未注册、也不构建**的上游目标（因此不产生 app.exec() 挂死风险）：
  - X11 门控的 `kwindowsystem_unit_tests()`（12 个）与
    `kwindowsystem_executable_tests()`（3 个）：`if(X11_FOUND)` 为假，根本不进入配置；
  - `tests/` 下的 `blurbehindtest`、`backgroundcontrasttest`：`add_executable` +
    `ecm_mark_as_test`。`ecm_mark_as_test` 只设 `EXCLUDE_FROM_ALL` 并归入
    `tests` 自定义目标，**不调用 add_test**，所以默认构建与 ctest 都不会跑它们
    （两者是交互式 GUI 演示程序）。
- 结论：`ctest --test-dir <build> --output-on-failure --no-tests=error`
  的注册集合非空（满足 `--no-tests=error`），1/1 通过，通过率 100%。

## 消费测试（test_package）

三个可执行 + CTest 注册（`test()` 里逐个直跑，共 29 条断言）：

1. `test_kf5windowsystem`（9 条）：链接 `KF5::WindowSystem` + `Qt5::Gui`，在 offscreen QPA 下
   断言 dummy 后端的可观测行为——`platform()==Platform::Unknown`、
   `isPlatformX11()/isPlatformWayland()` 均为 false、单例及其 meta object 存活、
   `showingDesktop()/allowedActionsSupported()` 为 false、
   `setShowingDesktop(true)` 是空操作、`KWindowEffects::isEffectAvailable()`
   对 BlurBehind / BackgroundContrast 为 false。
2. `test_kf5windowsystem_harmonyos`（5 条）：`__OHOS__` 门控——`uname` 的 sysname 属于
   {HarmonyOS, OpenHarmony, OHOS}、machine 为 aarch64、`KWindowSystem`
   的 meta object 类名正确、且 OHOS 不宣称 X11/Wayland 后端。
3. `test_kf5windowsystem_artifacts.py`（15 条）：对**安装后的制品树**做结构化校验
   （纯 stdlib，只读 ELF 头/节表/动态段，不 grep 二进制）——`lib/` 下恰好一个实体
   `libKF5WindowSystem.so*`、`.so` 开发链接存在、ELFCLASS64/ELFDATA2LSB/EV_CURRENT、
   `e_type==ET_DYN`、`e_machine==EM_AARCH64`、`.text`、`.codesign`、
   `DT_SONAME` 存在且以 `libKF5WindowSystem.so` 开头并指向 `lib/` 里真实存在的文件、
   以及 `include/` 下的 `KWindowSystem` 头与 `lib/cmake` 下的
   `KF5WindowSystemConfig.cmake` 均已安装。

其中 **9 条为鸿蒙特有**（harmonyos 二进制的 5 条 + 制品侧的 AArch64 机器类型、
`.codesign` 段、DT_SONAME 存在与闭环 4 条）。

## 依赖版本

- qt5-qtbase/5.15.2.2
- ecm/6.26.0 (tool_requires)

## 验证结果

`conan create` PASS（详见 PR 描述中的验证结果段）。
