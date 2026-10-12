# kplotting5 5.116.0 适配笔记（KDE Frameworks 5 / Qt5）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-06
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++（OHOS 工具链）
- 状态: built（conan create 全绿 RC=0，上游测试 4/4 + test_package 37/37）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（host==build，原生轨）
- 任务卡: OHPCD #14900，taskBranch `feat/kplotting5-5.116.0`，账号 j669539

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Core/Gui/Widgets/Test 运行时与 moc/rcc/uic（含 widgets；5.15.2 为 -no-widgets 旧版，不可用） |
| ecm | 6.26.0 | Extra CMake Modules（KDEInstallDirs、KDECMakeSettings、ECMAddTests、ECMGenerateHeaders 等，tool_requires） |

kplotting 是 KF5 Tier 1 件：**无任何 KF5 库依赖**（仅 Qt5Widgets + ECM），
依赖面是 kpeople5/kcalcore 系 KF5 件里最轻的。

## 编译步骤

1. 源码: `https://download.kde.org/stable/frameworks/5.116/kplotting-5.116.0.tar.xz`
   sha256 `bc3703f2ccd5d9d6a5e881a9476a6d21b2722aecbe5dfe48c03d1008772be579`
   （本地实测 + download.kde.org 官方 `.sha256` 边车文件双源一致）
2. 上游是标准 KF5 CMake 工程: `find_package(ECM 5.116.0 NO_MODULE)` +
   `find_package(Qt5 5.15.2 REQUIRED NO_MODULE Widgets)`，产物 `libKF5Plotting.so`
   （KPlotWidget/KPlotObject/KPlotPoint/KPlotAxis 四类，Qwt 风格绘图）。
3. `conan create archives/k/kplotting5/5.116.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
   --build=missing --user=ohpcd --channel=stable`
   → `cmake.configure()` → `cmake.build()` → `ctest`（build 内执行上游测试）→
   test_package。干净重跑（remove -c 后重编）全绿 RC=0。
   配置参数: `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
   `KF_SKIP_PO_PROCESSING=ON`、`BUILD_DESIGNERPLUGIN=OFF`、`BUILD_TESTING=ON`、
   `BUILD_SHARED_LIBS=ON`、`CMAKE_SYSTEM_NAME=Linux`（variables + cache_variables
   双覆盖）、`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + SONAME flags。
   ctest 运行环境: `QT_QPA_PLATFORM=offscreen`、`HOME=<build>/test-home`、
   `XDG_RUNTIME_DIR=<build>/xdg-runtime`、`LD_LIBRARY_PATH` 含依赖 lib 与
   `/system/lib64`。

## 关键适配点

- **CMAKE_SYSTEM_NAME=Linux（双覆盖，kcalcore5/5.116.0 先例）**: OHOS 的 Conan
  toolchain 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake ≥ 4 对其无
  platform module、不置 `UNIX`，并把构建判定为 cross-compiling。KPlotting 的 4 个
  上游 autotests 由 `ecm_add_tests()` 生成，而 ECM 仅在非 cross 构建时
  `add_test()`；同时 ECM 的 POSIX 编译标志/RPATH 处理在 `if(UNIX)` 下生效。
  配方用 `tc.variables` + `tc.cache_variables` 双写（cache 条目才能压过 toolchain
  自己的早期系统名探测），配对 `CMAKE_SYSTEM_PROCESSOR=aarch64`，既恢复 `UNIX=1`
  又让 4 个测试真正注册与构建（kcoreaddons5/kitemviews5/kpeople5 链式先例）。
- **BUILD_DESIGNERPLUGIN=OFF**: 该选项默认在非 cross 构建下为 ON；
  `src/designer` 依赖 Qt Designer 插件 API（Qt5Designer/Qt5UiPlugin），
  qt5-qtbase 不含，故显式关闭。
- **KF_SKIP_PO_PROCESSING=ON**: qtbase 不含 Qt5LinguistTools（lrelease/lconvert），
  用 ECM 上游开关跳过 poqm 处理（kcoreaddons5/kitemviews5 先例）。
- **使用 qt5-qtbase 原生 Qt5 CMake 配置**: `find_package(Qt5 ... NO_MODULE)` 需要
  原生 Qt5 config 提供的 `Qt5::Widgets/Qt5::Test` 与 CMake 宏；对 `qt5-qtbase` 设
  `cmake_find_mode=none`，并把 Qt 安装 prefix 加入 `CMAKE_PREFIX_PATH`。
- **mkspec 兼容**: `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码
  `<prefix>/../b/mkspecs/linux-clang`（构建树路径），打包缓存条目无此目录；
  helper `_prepare_qt_mkspec_compat()` 从包内 `mkspecs/` 重建整棵树
  （kcoreaddons5/kconfig5 先例）。
- **AUTOMOC/AUTORCC/AUTOUIC**: CMakeDeps 不导出 `Qt5::moc` 等可执行目标，
  用 `CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE` 指向 qt5-qtbase bin（4 个
  QTEST 二进制与 KPlotWidget/KPlotAxis 的 Q_OBJECT 都要过 moc）。
- **ELF RPATH 重写 → mmap PROT_EXEC 被拒（E537）**: CMake 在 install 阶段用
  `file(RPATH_CHANGE)` 原地改写 .so 的 RPATH；OHOS 拒绝 mmap PROT_EXEC 这类
  被改写后的库。`CMAKE_BUILD_WITH_INSTALL_RPATH=ON` 让链接器直接写最终 install
  RPATH，install 阶段无需改写。
- **未版本化 DT_SONAME**: `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"` → 可重定位的
  未版本化 DT_SONAME `libKF5Plotting.so`（W3 CI L5 soname gate）。
- **HMDFS jobserver fifo EPERM**: `CMAKE_BUILD_PARALLEL_LEVEL=1` 规避。
- **binary-sign-tool 签名**: `package()` 在 `cmake.install()` 后对包内每个
  relocatable ELF（libKF5Plotting.so）执行 OHOS 自签（llvm-objcopy 摘除旧
  `.codesign` → binary-sign-tool `sign -selfSign 1` → 校验回读 `.codesign` 节），
  复刻 kdsingleapplication/1.2.1 签名块。实测包内 lib 带 `.codesign` 节。
- **examples/**: 上游 5.116.0 tarball 无条件 `add_subdirectory(examples)`（无
  ENABLE_EXAMPLES 开关）。kplottest 演示程序链 KF5::Plotting + Qt5::Widgets，OHOS
  工具链下照常构建（消费侧验证公共头文件），上游未给 install() 规则 → 不入包，
  包交付物 = libKF5Plotting.so + 头文件 + cmake configs + mkspecs pri。

## 上游测试（R51）

清点（tarball 实测）: `autotests/` 4 个 QTEST 程序，全部经 `ecm_add_tests()`
注册 ctest：
- `kplotpointtest`（4 个 test* 函数: testConstructor/testPosition/testLabel/testBarWidth）
- `kplotaxistest`（5 个 test* 函数: testVisible/testTickLabelsShown/testLabel/testTickLabelFormat/testTickMarks）
- `kplotobjecttest`（15 个 test* 函数: testBrush…testClearPoints）
- `kplotwidgettest`（11 个 test* 函数: testPlotObjectsDefaultSize…testAntialiasing）

实跑（真机原生，build() 内 ctest）:
```
1/4 Test #1: kplotpointtest ...................   Passed    0.07 sec
2/4 Test #2: kplotaxistest ....................   Passed    0.06 sec
3/4 Test #3: kplotobjecttest ..................   Passed    0.05 sec
4/4 Test #4: kplotwidgettest ..................   Passed    0.05 sec
100% tests passed, 0 tests failed out of 4
```
（两轮构建均 4/4 100%，第一轮 0.09/0.05/0.06/0.05s，干净重跑 0.07/0.06/0.05/0.05s）

无排除项：全suite offscreen QPA 下无需会话总线/无显示服务器依赖，全部通过。

## test_package（R34 + R53）— 37/37 PASS

```
ok - libKF5Plotting.so is mapped into the process
ok - QApplication runs on the offscreen QPA platform
ok - packaged libKF5Plotting.so parses as ELF64
ok - DT_SONAME is the unversioned libKF5Plotting.so
ok - libKF5Plotting.so carries a DT_RUNPATH (E537)
ok - libKF5Plotting.so carries a .codesign section (OHOS signing)
ok - KPlotPoint::x() / y() / label() / barWidth() / setPosition() / setX()/setY()
ok - KPlotAxis::label() / setTickLabelFormat(char) / tickLabelWidth() / tickLabelPrecision()
ok - KPlotAxis::setTickMarks() major ticks / minorTickMarks() accessible
ok - KPlotObject::setPen() / setBrush() / size() / addPoint() x3 / removePoint()
ok - KPlotObject::points() ordering / clearPoints()
ok - KPlotWidget::setLimits()/dataRect() / addPlotObject() / addPlotObjects()
ok - KPlotWidget::replacePlotObject() / setBackgroundColor() / setForegroundColor()
ok - KPlotWidget::setGridColor() / setShowGrid(false|true) / setAntialiasing()
ok - KPlotWidget::set*Padding() / removeAllPlotObjects()
SUMMARY: 37 passed, 0 failed
```

ELF 实测（成品包 llvm-readelf/llvm-objdump）:
- SONAME: `libKF5Plotting.so`（未版本化）
- RUNPATH: `<pkg>/lib:<qt5-qtbase>/lib`
- `.codesign` 节: 1（binary-sign-tool 自签）

## 产物（L2/L5）

- `lib/libKF5Plotting.so`（共享库，L5 lib 有内容 ✓）
- `include/KF5/KPlotting/`（KPlotAxis/KPlotObject/KPlotPoint/KPlotWidget + kplotting_export.h + kplotting_version.h）
- `lib/cmake/KF5Plotting/`（KF5PlottingConfig.cmake/ConfigVersion/Targets）
- `mkspecs/modules/qt_KPlotting.pri`（ECMGeneratePriFile）
- 无 bin/（examples 上游无 install 规则，见上）
