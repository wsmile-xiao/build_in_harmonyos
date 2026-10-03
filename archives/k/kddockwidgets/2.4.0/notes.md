# kddockwidgets 2.4.0 适配笔记（HarmonyOS PC）

## 上游概况

- 上游：KDAB/KDDockWidgets v2.4.0（GitHub release tarball）
- 许可证：GPL-2.0-only OR GPL-3.0-only
- 构建：CMake ≥3.15，纯 C++17，无必选第三方依赖
  - spdlog/fmt：QUIET 可选（配方 `KDDockWidgets_NO_SPDLOG=ON` 显式关断）
  - nlohmann_json/kdbindings：QUIET + `src/3rdparty/` 自带回退，无需外部包
- 前端：qtwidgets / qtquick / flutter。上游自 v2.3.0 起默认 Qt6，Qt5 为受支持配置（`QT_MIN_VERSION 5.15`）

## 适配策略（recipe 层，零源码补丁）

| 配置 | 值 | 理由 |
|------|-----|------|
| KDDockWidgets_QT6 | OFF | OHOS 制品仓提供 Qt5 栈（qt5-qtbase/5.15.2.2：Core/Gui/Widgets/Test + offscreen QPA） |
| KDDockWidgets_FRONTENDS | qtwidgets | qtquick 需 Qt5 Quick/QuickControls2 + OHOS QPA 上可用 scenegraph；qtwidgets 为上游主 C++ API |
| KDDockWidgets_EXAMPLES | OFF | GUI 示例非库本体 |
| KDDockWidgets_TESTS | ON | 构建上游 autotest 全套（qtwidgets 前端） |
| KDDockWidgets_DEVELOPER_MODE | ON | 上游 `add_subdirectory(tests)` 被 `KDDockWidgets_TESTS AND KDDockWidgets_DEVELOPER_MODE` 双重门控（CMakeLists.txt:620 "Always build the test harness in developer-mode"）；dev 模式仅追加 `-Wall/-Wextra` + PRIVATE `QT_FORCE_ASSERTS` + 库目标两个 PUBLIC 宏（gcc>14 `-fhardened` 分支与 spdlog REQUIRE 分支在本配置跳过） |
| KDDockWidgets_NO_SPDLOG | ON | 消除 QUIET 可选依赖分叉 |
| KDDockWidgets_X11EXTRAS | OFF | OHOS 无 X11，Qt5 分支会追加 Qt5::X11Extras |
| shared | ON | 与 qt5-qtbase（shared-library）一致 |

Qt5 桥接（沿用 kglobalaccel/attica5 已验证模式）：
- `CMakeDeps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")` 重新生成干净 Qt5Config
- `CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE` 指向 qt5-qtbase `bin/{moc,rcc,uic}`（本配方比 kglobalaccel 多 uic：tests/CMakeLists.txt 对 qtwidgets 开启 AUTOUIC，编译 mainwindow.ui）
- `_prepare_qt_mkspec_compat`：镜像 `mkspecs/linux-clang` 到 `<qt_pkg>/../b/`（Qt5CoreConfigExtras 探测烘焙构建目录）
- `-isystem <qt_pkg>/mkspecs/linux-clang`（autotest 含 `<qplatformdefs.h>`）
- SONAME 三件套：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + C/CXX SONAME flag（L5 门禁）
- `CMAKE_PROJECT_INCLUDE` 注入 imported `Qt5::qmake` target → qt5-qtbase 的 `bin/qmake`：
  CMakeDeps 生成的 Qt5Config 无 qmake 组件，而上游 `CMakeLists.txt:302` 无条件
  `include(KDQtInstallPaths)`（要求 Qt5::qmake/qtpaths target 并执行 `qmake -query`），
  否则 configure 直接 FATAL "No supported Qt version found"。qmake 为 OHOS 构建，
  真机可原生执行；`-query` 输出仅用于 .pri 文件生成（ECM_MKSPECS_INSTALL_DIR 兜底
  相对路径 `mkspecs/modules`）。真机首轮 G2 实测踩中此坑后修复。
- 同一注入文件追加 `Qt5::WidgetsPrivate` INTERFACE IMPORTED → 链接 `Qt5::Widgets`
  并暴露 Qt private 头根目录：
  上游 `src/CMakeLists.txt:381` 对 qtwidgets 前端无条件 PRIVATE 链接 WidgetsPrivate。
  本配置（Qt5、X11EXTRAS=OFF）实际用到的私有头仅
  `QtGui/private/qhighdpiscaling_p.h`（core/WidgetResizeHandler.cpp:40、
  qtcommon/Window.cpp:22，常编译）+ 其依赖 `QtCore/private/qglobal_p.h`；
  其余 private 包含属未构建的 qtquick 前端或 Qt6-only 的 qtx11extras_p.h 分支。
  qt5-qtbase/5.15.2.2 的 CMakeDeps 组件无 WidgetsPrivate → 第 3 轮 configure 报
  "Target Qt5::WidgetsPrivate was not found"；映射到公开 Qt5::Widgets（同一 .so）
  后第 4 轮又报 private 头找不到（CMakeDeps 组件 include 根只有 include/，不含
  `include/<Module>/5.15.2` 私有根）。制品实际带齐私有头
  （include/QtGui/5.15.2/QtGui/private/… 真机实证）→ 注入 target 追加
  INTERFACE_INCLUDE_DIRECTORIES（QtGui/QtCore/QtWidgets 的 5.15.2 根，配方内按
  存在性探测）。第 3/4 轮 G2 实测踩中此坑后修复。
- 同一注入文件追加 `add_compile_options(-include <shim>)`：
  OHOS Qt5 port（qt5-qtbase/5.15.2.2）裁剪了 stock Qt 5.15 testlib 的窗口辅助
  API（qtest_gui.h/qtest_widgets.h 尾部 `QTest::qWaitForWindowActive/Exposed`
  整节被删，QtGui include 链也不再补全 QWindow/QGuiApplication）。上游
  tst_qtwidgets.cpp:3083 用 `QTest::qWaitForWindowActive(QWidget*)`、
  tst_native_qpa.cpp 解引用 QWindow/qGuiApp（tst_native_qpa 每个用例自带
  offscreen 提前 return 守卫，上游设计即"仅原生 QPA 全跑"）→ generate() 写
  shim 头 kddw_qt_windowactive_shim.h（stock 语义：轮询 windowHandle()->isActive()
  至超时；offscreen QPA 模拟激活，真机探针 QWindow/QWidget active=1/1 实证）
  并经 add_compile_options 强制包含进全部 TU，上游源码零改动。
  第 8 轮 G2 实测踩中此坑后修复。

## 上游测试清单（R51）

上游 qtwidgets 前端注册的 ctest 用例（tests/CMakeLists.txt）：
`tst_qtwidgets`（qtwidgets/tst_qtwidgets.cpp + mainwindow.ui）+ 核心套件 23 个：
`tst_docks`、`tst_docks_slow1`…`tst_docks_slow8`、`tst_multisplitter`、`tst_viewguard`、
`tst_view`、`tst_window`、`tst_droparea`、`tst_platform`、`tst_group`、`tst_titlebar`、
`tst_stack`、`tst_tabbar`、`tst_separator`、`tst_floatingwindow`、`tst_dockwidget`、
`tst_native_qpa`。真机 `ctest -N` 实测共 **24 例**（reports/upstream-test-inventory.txt）。

三步法：
1. **盘点**：配方 `build()` 内 `ctest -N`（构建日志可查）
2. **执行**：真机全量 `ctest`，环境：`QT_QPA_PLATFORM=offscreen`（qt5-qtbase 带 offscreen 插件，`-no-xcb` 后唯一无头方案）、`QT_PLUGIN_PATH=<qt5>/plugins`、LD_LIBRARY_PATH 注入依赖与构建树
   - **坑**：OHOS musl 加载器忽略 ELF RUNPATH 只认 LD_LIBRARY_PATH；conanrun.sh 只带依赖包库目录（qt5 等），不含本包构建树 `lib/`（`libkddockwidgets.so` 落在 `build/Release/lib/`，bin/ 只有可执行）→ 首轮全量 24 例 0.05-0.09s 速败（Error loading shared library libkddockwidgets.so）。修复：ctest 脚本显式 `export LD_LIBRARY_PATH="$BUILD/lib:/system/lib64:$LD_LIBRARY_PATH"`；tst_native_qpa 单测预检 EXIT=0 后重跑全量
3. **报告**：`reports/test-report.md`（逐例通过/跳过明细 + 退出码），二进制哈希 `reports/upstream-test-binary.txt`

## 消费者测试（test_package）

R34 真实 API 用法，12 个测试用例走用例执行器（runCase：逐例
`TEST PASS/FAIL` 输出 + `SUMMARY: n/12 passed` + 任一失败进程退出 1——
rule12 要求测试执行器而非纯断言，jakarta-auth 整改先例）：
双 DockWidget 停靠场景 —— uniqueName 回读、title/setTitle 回环、
isFloating 状态、DockRegistry 计数、LayoutSaver saveToFile/restoreFromFile
布局文件回环（close 后 restore 复原）。全部用例在 offscreen 无头环境
确定性成立。

## 真机验证（2026-09-30，通道 3）

- **conan-verify 八门禁全 PASS**（2026-09-30T09:10:34，第 11 轮 = 最终树；reports/conan-verify-report.md）：
  G0（E092 已知风险已处理）/ G1（配方完整性 + R26/R28）/ G2（conan create 干净构建成功，
  reports/conan-create.log 尾部逐例 `TEST PASS` ×12 + `SUMMARY: 12/12 passed, 0 failed`）/
  G3（无 bin/ 纯库包，R26 通过）/ G4（PASS）/ L2·L4·L5（无 cache 路径跳过 PASS）。
  第 9 轮（01:49:04）曾以 R46 终态上报（draft:false）；第 10/11 轮 launch 环境无
  --out/OHC_RESULT_OUT，R46 走兜底草稿落盘（milestone=conan_verify_passed），
  八门禁裁决与报告不受影响。
- **消费者测试 12/12 PASS**（G2 内 test_package 实跑，offscreen QPA，真机；
  第 11 轮为 rule12 执行器整改后复验，见下）。
- 第 1/3/4/5/7 轮 G2 分别踩中 qmake target 缺失 / WidgetsPrivate target 缺失 / private 头
  找不到 / 探测守卫自坑 / Qt5Test standalone config 缺失，第 8 轮踩中 OHOS testlib
  窗口 API 裁剪（见上文 Qt5 桥接第 6 条），第 9 轮全绿；第 10 轮（03:28:20）复验全绿
  ——第 9→10 轮配方仅两处改动：docstring 测试计数 22→23 修正 + `_runtime_env` 的
  LD_LIBRARY_PATH 补上构建树 `lib/`（对齐第 7 坑结论）。第 11 轮（09:10:34）复验全绿
  ——第 10→11 轮改动：docstring 测试计数对齐 ctest 权威清单 24 例（tst_qtwidgets +
  23 核心）+ 消费者测试 rule12 整改（断言堆 → 用例执行器）。
- 上游 ctest 全量执行（R51 第 2 步）：**24/24 通过（100%，CTEST-EXIT=0，总耗时
  743.50s）**。首轮全挂（LD_LIBRARY_PATH 缺构建树 lib/，见上文三步法坑位），修复后
  第二轮全量全过；逐例明细见 reports/test-report.md，二进制哈希见
  reports/upstream-test-binary.txt。

## 已知限制

- qtquick 前端未构建（Qt5 Quick/QuickControls2 依赖 qt5-qtdeclarative，且 OHOS QPA 下
  scenegraph 可用性未验证）；上游 qtwidgets 前端与核心 API 已全覆盖
- tst_docks_slow* 为上游慢速套件（真实交互时序），offscreen 下执行时长较长，
  真机执行时以实际通过/跳过为准
