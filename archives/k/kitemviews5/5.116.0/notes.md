# kitemviews5 5.116.0 适配笔记（KDE Frameworks 5 / Qt5）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++（OHOS 工具链）
- 状态: built（conan-verify PASS，未 upload）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（host==build，原生轨）

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Core/Gui/Widgets/Test 运行时与 moc/rcc/uic（含 widgets；5.15.2 为 -no-widgets 旧版，不可用） |
| ecm | 6.26.0 | Extra CMake Modules（KDEInstallDirs、KDECMakeSettings、ECMAddTests、ECMGenerateHeaders 等，tool_requires） |

## 编译步骤

1. 源码: `https://download.kde.org/stable/frameworks/5.116/kitemviews-5.116.0.tar.xz`
   sha256 `6c0efbf408dab60c58bb13bb3a7488827283a5eea947ef3cfd0fbcb4f09e01eb`（实测）
2. 上游是标准 KF5 CMake 工程: `find_package(ECM 5.116.0 NO_MODULE)` +
   `find_package(Qt5 5.15.2 CONFIG REQUIRED Widgets)`，产物 `libKF5ItemViews.so`。
3. `conan create`（干净构建，实测 13 个 src 目标文件重编）→ `cmake.configure()` →
   `cmake.build()` → `ctest`（build 内执行上游测试）→ test_package。
   配置参数: `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
   `KF_SKIP_PO_PROCESSING=ON`、`BUILD_DESIGNERPLUGIN=OFF`、`BUILD_TESTING=ON`、
   `BUILD_SHARED_LIBS=ON`、`CMAKE_SYSTEM_NAME=Linux`、
   `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + SONAME flags。
   ctest 运行环境: `QT_QPA_PLATFORM=offscreen`、`HOME=<build>/test-home`、
   `XDG_RUNTIME_DIR=<build>/xdg-runtime`、`LD_LIBRARY_PATH` 含依赖 lib 与
   `/system/lib64`。

## 关键适配点

- **CMAKE_SYSTEM_NAME=Linux（UNIX-like 原生目标）**: OHOS 的 Conan toolchain 把
  `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 对其无 platform module
  且不置 `UNIX`，并把构建判定为 cross-compiling。KItemViews 的 4 个上游测试中
  唯一 ctest 注册项由 `ecm_add_test()` 生成，而 ECM 仅在非 cross 构建时
  `add_test()`；同时 ECM 的 POSIX 编译标志/RPATH 处理在 `if(UNIX)` 下生效。
  显式固定为 Linux（同 libc/同 clang 驱动的 Linux-like 目标）既恢复 `UNIX=1`
  又让测试真正注册与构建，是本链通用做法（kcoreaddons5）。
- **BUILD_DESIGNERPLUGIN=OFF**: 该选项默认在非 cross 构建下为 ON；
  `src/designer` 依赖 Qt Designer 插件 API（Qt5Designer/Qt5UiPlugin），
  qt5-qtbase 不含，故显式关闭。
- **KF_SKIP_PO_PROCESSING=ON**: qtbase 不含 Qt5LinguistTools（lrelease/lconvert），
  顶层 `ecm_install_po_files_as_qm(poqm)` 会因 `find_package(Qt5LinguistTools)`
  失败；用 ECM 上游开关跳过（kcoreaddons5/kconfig5 先例）。
- **使用 qt5-qtbase 原生 Qt5 CMake 配置**: `find_package(Qt5 ... CONFIG REQUIRED
  Widgets)` 需要原生 Qt5 config 提供的 `Qt5::Widgets/Qt5::Test` 与 CMake 宏；
  对 `qt5-qtbase` 设 `cmake_find_mode=none`，并把 Qt 安装 prefix 加入
  `CMAKE_PREFIX_PATH`（CMakeDeps 生成的 Qt5 config 会遮蔽原生配置）。
- **mkspec 兼容**: `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码
  `<prefix>/../b/mkspecs/linux-clang`（构建树路径），打包缓存条目无此目录；
  helper `_prepare_qt_mkspec_compat()` 从包内 `mkspecs/` 重建整棵树
  （kcoreaddons5/kconfig5 先例）。
- **AUTOMOC/AUTORCC/AUTOUIC**: CMakeDeps 不导出 `Qt5::moc` 等可执行目标，
  用 `CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE` 指向 qt5-qtbase bin。
- **ELF RPATH 重写 → mmap PROT_EXEC 被拒（E537 类）**: CMake 在 install 阶段用
  `file(RPATH_CHANGE)` 原地改写 .so 的 RPATH；OHOS 拒绝 mmap PROT_EXEC 这类
  “链接后被改写”的 ELF，运行时 `Error loading shared library libKF5ItemViews.so:
  Permission denied`。修复：`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，让链接器直接
  写入最终 install RPATH，install 阶段无需再改写（链接期修复，非 patchelf）。
- **SONAME**: `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"` → 产出无版本号但带
  可重定位 DT_SONAME `libKF5ItemViews.so`（W3 CI L5 soname 门禁）。
- **HMDFS / libc++**: `CMAKE_BUILD_PARALLEL_LEVEL=1`（HMDFS 拒绝 make jobserver
  fifo：`make: jobserver mkfifo: ... Operation not permitted`）；ctest 环境把
  `/system/lib64` 前置到 `LD_LIBRARY_PATH`，避免沙箱内不兼容的
  `libc++_shared.so` 抢占（kcoreaddons5/kconfig5 先例）。

## 源码修改（补丁）

无。所有适配均通过上游 CMake 开关 / Conan 配方变量完成，未修改上游源码
（`patches_applied: []`，patches/ 为空）。

## 上游测试（R51 三步法）

### 清点（tarball 实测）
- `autotests/` 目录: 1 个测试源（`klistwidgetsearchlinetest.cpp`），经
  `autotests/CMakeLists.txt` 的 `ecm_add_test(... TEST_NAME
  kitemviews-klistwidgetsearchlinetest ...)` 注册。
- `tests/` 目录: 3 个可执行程序（`kcategorizedviewtest.cpp`、
  `kwidgetitemdelegatetest.cpp`、`ktreewidgetsearchlinetest.cpp`），由
  `tests/CMakeLists.txt` 的 `add_executable` + `ecm_mark_as_test` 构建。
- **ctest 注册数实测 = 1**（`ctest` 输出 `1/1 Test #1:
  kitemviews-klistwidgetsearchlinetest ... Passed`）。`tests/` 的 3 个程序
  **未被 ctest 注册**：ECM 的 `ecm_mark_as_test()` 不调用 `add_test()`
  （其实现仅在 `BUILD_TESTING=OFF` 时把目标 `EXCLUDE_FROM_ALL` 挂到
  `buildtests`），实测 `build/Release/tests/CTestTestfile.cmake` 为空。

### 运行结果（真机 OHOS PC 原生执行）
| 项 | N | 实际运行 N′ | 结果 |
|----|---|------------|------|
| ctest 注册项 `kitemviews-klistwidgetsearchlinetest` | 1 | 1 | **1/1 通过**（`100% tests passed, 0 tests failed out of 1`） |
| `tests/` 交互式 GUI 程序（未注册 ctest） | 3 | 3（启动级） | 见下 |

- 合计（ctest 注册口径）: N=1，实际运行 N′=1，通过率 **100%**。
- `tests/` 的 3 个程序是**交互式 GUI 示例**（`kcategorizedviewtest` 与
  `kwidgetitemdelegatetest` 进入 `app.exec()`，`ktreewidgetsearchlinetest`
  进入 `QDialog::exec()`），**不含任何断言**，需要真实显示与人工交互，无法
  自动化判定通过。为取得可执行证据，三者在 `QT_QPA_PLATFORM=offscreen` 下用
  `timeout 5` 实跑：均成功初始化 KItemViews 控件并进入事件循环，直到超时被
  终止（rc=124，未崩溃）；其中 `kwidgetitemdelegatetest` 实际走到了
  KWidgetItemDelegate 的 `createItemWidgets` 路径（打印 `kf.itemviews: User of
  KWidgetItemDelegate should not delete widgets created by createItemWidgets!`）。
  证据日志: `~/tmp/kitemviews5-gui-demos/*.log`。
- 无 ctest 排除项。

### 复现命令
`conan create <archive> -pr:h=ci/conan/profiles/ohos-aarch64
-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
（build() 内 `ctest --test-dir <build_folder> --output-on-failure --no-tests=error`）
取证: `reports/conan-create.log`（`1/1 Test #1 ... Passed`，
`100% tests passed, 0 tests failed out of 1`）。

## 鸿蒙特有测试（R53）

`test_package/test.cpp` 链接 `KF5::ItemViews`，在 OHOS 上实际运行并断言
**16/16 通过**（`SUMMARY: 16 passed, 0 failed`）：

HarmonyOS 适配路径断言（4 条）:
1. `QApplication::platformName() == "offscreen"` —— Widgets 库在 OHOS 上通过
   offscreen QPA 平台插件无显示运行（GUI 适配路径）。
2. `libKF5ItemViews.so` 已映射进进程（`/proc/self/maps`）。
3. 该库带**无版本号 DT_SONAME** `libKF5ItemViews.so`
   （`CMAKE_PLATFORM_NO_VERSIONED_SONAME` 适配，实测 readelf 一致）。
4. 该库带 **DT_RUNPATH**（E537：`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，安装 ELF
   不被二次改写仍可被 OHOS 加载；实测 RUNPATH 存在）。

功能 API 断言（12 条，真实调用）:
- `KListWidgetSearchLine`：`listWidget()` 往返；按 `updateSearch("an")` 过滤
  QListWidget（banana 可见、apple/cherry 隐藏）；空搜索恢复。
- `KTreeWidgetSearchLine`：`treeWidget()` 往返；过滤 QTreeWidget 项。
- `KFilterProxySearchLine`：暴露 `lineEdit()`；`setText("ban")` 驱动
  `QSortFilterProxyModel` 过滤（rowCount=1 且余下 "banana"）。
- `KCategorizedSortFilterProxyModel`：默认非分类；`setCategorizedModel(true)`
  生效；按 `CategorySortRole` 排序后分类有序。
- `KCategorizedView` + `KCategoryDrawer`：`setModel`/`setCategoryDrawer` 往返。

## 验证结果

- `ohc-run.py conan-verify kitemviews5 5.116.0`：G0-G4 / L2/L4/L5 全部 PASS
  （`G2 conan create 成功`；G3 `无系统同名库冲突`；报告
  `reports/conan-verify-report.md` verdict=PASS）。未 upload，故 manifest 标
  `built`。
- test_package: 16/16 断言通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libKF5ItemViews.so` | 主库，`DT_SONAME=libKF5ItemViews.so`，含 RUNPATH |
| `include/KF5/KItemViews/*.h` | 公开头（含 kitemviews_export.h、kitemviews_debug.h） |
| `lib/cmake/KF5ItemViews/*` | CMake 包配置（KF5::ItemViews 目标） |
| `mkspecs/modules/qt_KItemViews.pri` | qmake .pri（KDE_INSTALL_USE_QT_SYS_PATHS=OFF → 包内相对路径） |

## 注意事项

- 本配方骨架与 kcoreaddons5/kconfig5 同源，可复用于后续 KF5（Qt5）库
  （同 qt5-qtbase/5.15.2.2 + ecm/6.26.0）。
- 若下游出现 `Error loading shared library ... Permission denied`，优先检查是否
  触发了 install 期 RPATH 原地改写（E537 类），固定手段 =
  `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`。
- **已知限制（RPATH，本配方不单独处理）**: `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`
  使安装产物的 RUNPATH 固化为构建机 Conan cache 绝对路径，产物本身非
  relocatable；消费者场景由 Conan RPATH / conanrun（LD_LIBRARY_PATH）兜底，
  已实测 test_package 通过。此为链上普遍现象（kcoreaddons5 等同），不在本配方
  单独处理。
- R32/R33 已遵守：未用 `os == "Linux"` 做 Conan 平台判断（配方用
  `str(self.settings.os) == "OHOS"`）；编译参数全部来自 Conan toolchain/依赖，
  无裸 `${CC}`/`${CFLAGS}`。
- R8/R49 已遵守：无源码补丁；未向共享 `/usr/local` 注入。
- R38：纯库包（无 `bin/`、`package_type="library"`），不建 `commands.json`
  （PF8 反向门禁）。
---

**编译结束**: 2026-09-18 18:24
**最终状态**: built
