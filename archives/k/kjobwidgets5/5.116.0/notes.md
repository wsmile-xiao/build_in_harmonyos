# kjobwidgets5 5.116.0 适配笔记

## 概要
KDE Frameworks 5 的 Qt5 作业进度组件库（libKF5JobWidgets.so）。把 KJob（来自
kcoreaddons）与展示作业进度的控件连接起来：KWidgetJobTracker（进度对话框）、
KStatusBarJobTracker（状态栏）、KUiServerJobTracker / KUiServerV2JobTracker、
KDialogJobUiDelegate，以及 KJobWidgets / KJobWindows 的窗口关联助手。

本包是 **kparts5 的直接构建依赖**（上游 `find_package(KF5JobWidgets ... REQUIRED)`）。
kparts5 自身的 10 个 REQUIRED 依赖中 7 个未发布（kio/kxmlgui/kservice/ktextwidgets/
kjobwidgets/kiconthemes/kconfigwidgets 的 KF5 分支在制品仓均无 5.116.0），故按
R36「依赖必须先发布再构建下游」先完成本依赖包。

## 编译环境
- 构建系统: cmake（ECM/KDEInstallDirs 骨架；CMake 4.1.2 + Ninja）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，cppstd 17）
- 状态: built

## 上游测试（R51 三步法）

### 1. 清点
| 位置 | 内容 | ctest 注册 |
|------|------|-----------|
| `autotests/` | 仅 `CMakeLists.txt`，其中的 `ecm_add_tests(footest.cpp ...)` 模板**被上游注释掉**（`#TODO: add tests`），目录内无任何测试源文件 | 0 |
| `tests/` | 2 个可执行程序：`kjobtrackerstest.cpp`、`kjobcreator.cpp`（含 `kjobcreator.ui`，经 `qt_wrap_ui` 处理） | 0（见下） |
| `src/` | 库源码，无测试 | 0 |

`tests/CMakeLists.txt` 用 `add_executable` + **`ecm_mark_as_test()`** 构建两个程序。
`ecm_mark_as_test()` 只给目标打 `LABELS`/`TESTS` 属性，**不调用 `add_test()`**
（同链先例 kitemviews5 实测 `build/Release/tests/CTestTestfile.cmake` 为空），
因此 ctest 套件为空：实测 `ctest -N` 输出 `Total Tests: 0`。

**结论：上游 ctest 注册数 N = 0。** 因套件为空，`build()` 内**不嵌入 ctest**
（空套件 rc=0 会制造 L1「假测试痕迹」，同链先例已将其列为知识条目）。

### 2. 运行
两个 `tests/` 程序是**交互式 GUI 演示**（`kjobtrackerstest` 用 KTestJob 驱动三种
tracker，`kjobcreator` 是手动调节作业状态的对话框），两者都以
`return app.exec();` 结束，**无退出路径、无任何断言**，需要真实显示与人工观察，
无法自动化判定通过。

二者在本 worker 沙箱**未能执行**：沙箱加载器不解析 `LD_LIBRARY_PATH`（实测给出
正确库路径后仍报 `Error loading shared library libKF5CoreAddons.so.5`），且拒绝
执行用户路径 ELF（rc=127）。**故未取得启动级证据**，仅确认二者被成功构建
（`bin/kjobtrackerstest`、`bin/kjobcreator`）。技术原因与实测输出见
`reports/test-report.md`。

### 3. 回填
- ctest 口径：N=0，N′=0（套件为空，无注册项可运行）——如实申报，不做占位。
- `tests/` 交互式程序：未运行（沙箱限制，rc=127），不计入通过率。

## 依赖版本
- `qt5-qtbase/5.15.2.2`：必须用 **.2 变体**。plain `5.15.2` 是不含 Widgets 的桩
  （实测无 `lib/cmake/Qt5Widgets`），而上游 `find_package(Qt5 ... Widgets)` 为
  REQUIRED；.2 同时提供 Qt5DBus（上游 `if(NOT ANDROID) find_package(Qt5 ... DBus
  REQUIRED)` 需要）与 Qt5Test。
- `kcoreaddons5/5.116.0`：PUBLIC 依赖（提供 `KJob`）。
- `kwidgetsaddons5/5.116.0`：PRIVATE 依赖（`KSqueezedTextLabel`）。
- `ecm/6.26.0`（tool_requires）：满足 `find_package(ECM 5.116.0)`。

## 关键适配决策

1. **CMAKE_SYSTEM_NAME=Linux**（同链通用做法）：OHOS Conan 工具链把 `os=OHOS`
   映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 既无该平台模块也不置 `UNIX`，
   且把构建判定为 cross-compiling。后果：ECM 的 POSIX 编译标志/RPATH 处理
   （`if(UNIX)`）失效，且 ECM 仅在非 cross 构建时注册 ctest（
   `if(NOT CMAKE_CROSSCOMPILING)`）。强制 Linux 平台（同 libc / 同 clang 驱动）
   恢复 `UNIX=1` 与原生构建语义。

2. **WITH_X11=OFF**：上游对非 APPLE 平台执行 `find_package(X11)`（**非
   REQUIRED**），命中后要求 `Qt5X11Extras`。OHOS 无窗口系统也无 X11 头
   （实测 `/usr/include/X11` 与 SDK include 均无 `Xlib.h`），`X11_FOUND` 为假、
   `HAVE_X11=0`，`kdialogjobuidelegate.cpp` 中的 `QX11Info` 分支被编译剔除
   （`config-kjobwidgets.h.cmake` 的 `#cmakedefine01 HAVE_X11`）。
   显式置 OFF 使行为确定，不依赖探测偶然结果。

3. **SONAME 三件套（E537）**：OHOS CMake 平台模块未定义
   `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG`，产出的 `.so` 无 `DT_SONAME`，
   消费者链接后 `DT_NEEDED` 记录路径形式（`bin/libKF5JobWidgets.so`）导致运行时
   无法解析。修复：
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,` +
   `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`（后者让安装期不再原地改写 ELF 的
   `RPATH`，否则 OHOS 拒绝把被改写过的 `.so` 以 `PROT_EXEC` mmap）。

4. **poqm 处理**：上游 `ecm_install_po_files_as_qm(poqm)` 会
   `find_package(Qt5LinguistTools CONFIG REQUIRED)`（lconvert/lrelease），
   qt5-qtbase 不含该组件。采用双保险：补丁注释掉该调用
   （`patches/0001-CMakeLists.txt.patch`）+ `KF_SKIP_PO_PROCESSING=ON`
   （同链 kguiaddons5 / kdbusaddons5 做法）。

5. **qt5-qtbase 走原生 Qt5 配置**：`CMakeDeps` 对 qt5-qtbase 设
   `cmake_find_mode=none`，改由 `conan_cmakedeps_paths.cmake` 把包的
   `lib/cmake`、`lib`、`include` 前置进 `CMAKE_PREFIX_PATH` /
   `CMAKE_LIBRARY_PATH` / `CMAKE_INCLUDE_PATH`，从而解析包内自带的
   `Qt5WidgetsConfig.cmake` 等（含 Qt5::Widgets/Qt5::DBus/Qt5::Test 目标与
   Qt5 宏）。`CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE` 显式指向包的
   `bin/moc|rcc|uic`（自动生成路径不提供 Qt5::moc 等导入目标）。

6. **mkspecs 兼容修复**：包内 `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码
   构建树路径 `<prefix>/../b/mkspecs/linux-clang`，打包产物不含该目录；`generate()`
   从包自身 `mkspecs/` 复制 `linux-clang` 与 `common` 到该位置，使
   `linux-clang/qplatformdefs.h` 的相对 include 得以解析（kcoreaddons5 /
   kconfig5 / kitemviews5 先例）。

7. **CMAKE_BUILD_PARALLEL_LEVEL=1**：HMDFS 缓存文件系统拒绝创建 make
   jobserver fifo（`mkfifo: Operation not permitted`）。

8. **测试/工具运行时库路径**：把 `/system/lib64` 前置到 `LD_LIBRARY_PATH`
   （沙箱下存在不兼容的 `libc++_shared.so`），并为已发布 KF5 二进制 DT_NEEDED
   中的构建树相对路径建 `bin/` 软链农场。

## 上游测试修改说明
**未修改任何上游测试用例**（上游只有 2 个交互式演示程序且未被 ctest 注册，
未对其做任何改动）。补丁 `0001-CMakeLists.txt.patch` 只注释掉顶层
`ecm_install_po_files_as_qm(poqm)` 这一构建步骤，不涉及测试代码。

## 补全测试说明
上游**无正式测试套件**（`autotests/` 为空模板，`tests/` 为交互式演示且未注册
ctest）。适配后由 `test_package/test.cpp` 补全消费者视角测试：链接
`KF5::JobWidgets` 并实际调用 `KJobWidgets::setWindow/window`、
`KJobWindows::setWindow/window`、`KWidgetJobTracker::registerJob/widget/
unregisterJob`、`KStatusBarJobTracker::setStatusBarMode/registerJob/widget`、
`KDialogJobUiDelegate::setWindow` 与 `KJob::setUiDelegate`，并附鸿蒙平台断言
（offscreen QPA 生效、已安装库为 ELF 且带无版本号 DT_SONAME 与 DT_RUNPATH）。
断言数见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 验证结果
见 `reports/conan-create.log`、`reports/conan-verify-report.md`、
`reports/test-report.md`。

## 注意事项
- 本包为**纯库**（产物只有 `lib/libKF5JobWidgets.so` 与头文件），**不创建**
  `commands.json`（R38：仅含 `bin/` 可执行产物的工具包需要）。
- 上游源位于 `download.kde.org/Attic/frameworks/5.116/`（KDE 官方域名，
  5.116 周期已归入 Attic 归档目录），非 `stable/` 路径，属官方正式源（R39）。
- 若后续 kparts5 立项，本包已发布后即可满足其 `KF5::JobWidgets` REQUIRED 依赖。
---

**编译结束**: 2026-09-27 16:57
**最终状态**: built
