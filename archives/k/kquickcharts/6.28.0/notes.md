# kquickcharts 6.28.0 适配笔记（OHOS / HarmonyOS PC aarch64）

## 一、软件概述

- kquickcharts：KDE Frameworks 6 的 Qt Quick Charts 库。纯 QML 模块，无公开 C++ 头文件。
  - QML 模块 `org.kde.quickcharts`：`BarChart` / `LineChart` / `PieChart` / `ChartDataSource` 系列
  - QML 模块 `org.kde.quickcharts.controls`：AxisLabels / GridLines / Legend 等控件
  - 产物：`libQuickCharts.so`、`libQuickChartsControls.so`、两个 QML 插件
- 顶层 CMakeLists 门槛：`cmake_minimum_required(VERSION 3.29)`、`REQUIRED_QT_VERSION 6.9.0`、
  `find_package(Qt6 CONFIG REQUIRED Qml Quick QuickControls2 ShaderTools)`、`find_package(ECM 6.28.0 NO_MODULE)`
- 构建系统：CMake + KDE ECM（`ecm_add_qml_module` / `qt6_add_shaders` / `ecm_generate_qdoc`）

## 二、W0 依赖预检表（实测）

| 依赖 | 版本 | 类型 | 制品仓实测 | 结论 |
|---|---|---|---|---|
| qtbase | 6.11.1 | requires | `conan download --only-recipe -r=ohpcd` OK（cache rev 714d84d…） | ✅ 已发布 |
| qtdeclarative | 6.11.1 | requires | `conan download --only-recipe -r=ohpcd` OK（cache rev 5e71bc8…） | ✅ 已发布 |
| qtshadertools | 6.11.1 | requires | `conan download --only-recipe -r=ohpcd` OK（remote rev 7bc99312…） | ✅ 已发布 |
| ecm | 6.28.0 | tool_requires | `conan list ecm/* -r=ohpcd` 仅有 6.20.0 / 6.26.0 / 7.0.7；`conan download ecm/6.28.0` → `error:system acceleration policy not enabled`（cnb.cool 对不存在配方的响应） | ❌ **未发布** |

> ⚠️ 任务描述中 W0 写“ecm/6.28.0 已发布”，但实测制品仓只有 ecm/6.26.0（与 attica/6.28.0、
> kdnssd/6.29.0 的经验一致）。采用既有方案：**降级到 ecm/6.26.0**，patch
> `0001-ohos-ecm-and-soname.patch` 把 `find_package(ECM 6.28.0)` 与 `KF_DEP_VERSION` 都降到 6.26.0
> （后者保证安装后的 `KF6QuickChartsConfig.cmake` 里 `find_dependency(ECM 6.26.0)`）。
> ecm/6.26.0 含 kquickcharts 用到的全部 ECM 模块（ECMQmlModule/ECMAddTests/ECMGenerateExportHeader/
> ECMDeprecationSettings/ECMGenerateQDoc/ECMSetupVersion/ECMQtDeclareLoggingCategory/KDEInstallDirs/
> KDEFrameworkCompilerSettings/KDECMakeSettings/KDEGitCommitHooks/ECMFeatureSummary），已验证。

## 三、OHOS 适配要点（逐项记录）

1. **qtbase 桥接（conan_cmakedeps_paths.cmake）**：qtbase 用 `cmake_find_mode=none`，CMakeDeps 不生成
   Qt6 target；`generate()` 手工写 `conan_cmakedeps_paths.cmake`（qtbase `lib/cmake` PREPEND 进
   CMAKE_PREFIX_PATH，lib/include 同步，`CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`），并显式设
   `Qt6_DIR`/`Qt6Qml_DIR`/`Qt6Quick_DIR`/`Qt6QuickControls2_DIR`/`Qt6QuickTest_DIR`/`Qt6ShaderTools_DIR`
   与 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（模式同 qtquicktimeline/6.11.1.1）。
2. **ECM 三个变量必须手工设置**（CMakeDeps 生成的 ECMConfig.cmake 都不提供）：
   - `ECM_MODULE_PATH` → ecm 包 `share/ECM/{modules,find-modules,kde-modules}`
   - `ECM_MODULE_DIR` → `share/ECM/modules/`（KDEInstallDirs 里 `include("${ECM_MODULE_DIR}/ECMQueryQt.cmake")`）
   - `ECM_GLOBAL_FIND_VERSION` → `6.26.0`（≥5.240 时 ECM QtVersionOption 默认 Qt6；缺省会判定 Qt5，
     KDEInstallDirs5/ECMQmlModule5 走 `add_library` → **CMP0002 同名 target 冲突**，configure 失败）
3. **SONAME 丢失（本包最关键的坑）**：`ecm_add_qml_module`→`qt_add_qml_module`(Qt 6.11) 会清掉 backing
   library target 的 VERSION/SOVERSION，导致 `.so` **无 DT_SONAME**。链接器于是把相对路径
   `../bin/libQuickCharts.so` 记进插件/测试二进制的 DT_NEEDED，运行时加载器**按 CWD 解析**该路径——
   真实部署（CWD 不含 `../bin`）直接 `Cannot load library … ../bin/libQuickCharts.so`。
   修复（patch + recipe）：
   - patch 在 src/controls 的 CMakeLists 里 `set_target_properties(... LINK_FLAGS "-Wl,-soname,libQuickCharts.so.1")`
   - recipe `build()` 在 build bin 目录创建 `libQuickCharts.so.1 → libQuickCharts.so` 等版本化软链
     （ctest 用）；`package()` 在包 lib 目录同样创建（部署用）
   - recipe `_strip_imported_no_soname` 把生成 cmake 里的 `IMPORTED_NO_SONAME … TRUE` 改为 FALSE
   - 验证：安装后插件 NEEDED=`libQuickCharts.so.1`，在无 `../bin` 的 CWD 下 `qml` 加载 org.kde.quickcharts
     成功（`CHART_TYPES_OK`）
4. **qt6_add_shaders**：编译期调用 `qsb`（qtshadertools 包里的 OHOS arm64 工具，本机可直接运行），
   但需要 qtbase/qtdeclarative/qtshadertools 的 lib 在 `LD_LIBRARY_PATH`（否则 `symbol not found`）。
   `build()` 里用 `_runtime_env()`（遍历 `self.dependencies` prepend `lib`）包住 `cmake.build()`。
5. **KF 平台检查**：`KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）。
6. **测试运行**：见下节。QML 测试需要 `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software` +
   `QML2_IMPORT_PATH/QML_IMPORT_PATH` 指向依赖 qml 目录与 build bin；`HOME/XDG_*` 隔离；
   `CTEST_PARALLEL_LEVEL=1`；`ctest --test-dir <build> --no-tests=error`。
7. **KDEGitCommitHooks**：非 git 仓库时打印 `fatal: not a git repository` 警告，非致命。
8. **签名**：`package()` 对包内所有 `.so` 做 OHOS ELF 签名（`llvm-objcopy` 去旧 `.codesign` +
   `binary-sign-tool sign -selfSign 1`），模式同 qtquicktimeline。

## 四、上游测试清点与实测（R51 三步法）

### 1. 上游测试清点（源码 autotests/）

- 测试目录：`autotests/`，`ecm_add_tests` 注册 4 个 C++ 测试 +
  `add_executable(qmltest …)` 驱动 3 个 QML 测试，共 **7 个 ctest 条目**：

| # | 测试名 | 类型 | 来源 |
|---|---|---|---|
| 1 | ArraySourceTest | C++ | autotests/ArraySourceTest.cpp |
| 2 | MapProxySourceTest | C++ | autotests/MapProxySourceTest.cpp |
| 3 | HistoryProxySourceTest | C++ | autotests/HistoryProxySourceTest.cpp |
| 4 | ItemBuilderTest | C++ | autotests/ItemBuilderTest.cpp |
| 5 | tst_BarChart.qml | QML (qmltest) | autotests/tst_BarChart.qml |
| 6 | tst_LineChart.qml | QML (qmltest) | autotests/tst_LineChart.qml |
| 7 | tst_PieChart.qml | QML (qmltest) | autotests/tst_PieChart.qml |

### 2. 实测结果（conan create，BUILD_TESTING=ON）

- 注册 N = **7**；实测 N' = **7**；通过 = **7/7（100%）**
- 运行环境：`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`，
  `LD_LIBRARY_PATH`=依赖 lib + build bin，`QML2_IMPORT_PATH`/`QML_IMPORT_PATH`=依赖 qml + build bin，
  `QT_PLUGIN_PATH`=依赖 plugins + build bin，`HOME/XDG_*` 隔离
- 完整日志：仓库外 `.tmp_work/kqc_cc/conan-create.log`（`100% tests passed, 0 tests failed out of 7`）

### 3. 逐项技术要点 / 曾失败项及原因

- 探索阶段曾全部失败：QML 3 项报
  `Error loading shared library ../bin/libQuickCharts.so (needed by bin/qmltest)` ——
  根因即第三节的 **SONAME 丢失**（qmltest 的 DT_NEEDED 为 CWD 相对路径）。加
  `-Wl,-soname` 后干净重链，全部二进制改引用 `libQuickCharts.so.1`，经 LD_LIBRARY_PATH 正常解析，7/7 通过。
- QML 测试依赖 offscreen + software 渲染**确实可运行**（证据：conan create 日志中
  tst_BarChart/tst_LineChart/tst_PieChart 均 Passed），不存在“没环境”问题。

## 五、构建记录

- 探索构建：手工 cmake（conan install 生成 toolchain + 手工 Qt6_DIR/ECM 变量），make -j8 成功。
- 正式构建：`conan create archives/k/kquickcharts/6.28.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
- 源码 SHA-256：`c5d361d90861b4cd3db861568da5279ae2b1cb953e874126c15abbd7138378e5`
- 包引用：`kquickcharts/6.28.0#4a528241afa71768b82276ec085df244:1b9180db9e62194d8376b684eec9400c9e837e9c`

## 六、test_package（R34 真实调用）

- `test_kquickcharts.cpp`：QGuiApplication + QQmlEngine，QML 文档 import `org.kde.quickcharts`，
  实例化 `BarChart`（并 `valueSources: [ArraySource]`）、`LineChart`、`PieChart`，
  `findChild` 断言三者存在，读回 `LineChart.lineWidth` / `PieChart.thickness` 属性。
- 链接：`Qt6::Qml Qt6::Quick` + 包内 `libQuickCharts.so`（UNKNOWN IMPORTED，真链）。
- 运行：offscreen + software；实测输出 `KQUICKCHARTS_TEST_OK: BarChart/LineChart/PieChart instantiated (lineWidth=3, thickness=0.5)`。

## 七、补丁

- `patches/0001-ohos-ecm-and-soname.patch`：
  1. 顶层 CMakeLists.txt：`find_package(ECM 6.28.0)`→`6.26.0`；`KF_DEP_VERSION`→`6.26.0`
     （使安装的 KF6QuickChartsConfig.cmake 依赖 ECM 6.26.0）
  2. src/CMakeLists.txt：`QuickCharts` 目标 `LINK_FLAGS "-Wl,-soname,libQuickCharts.so.${KF6QuickCharts_SOVERSION}"`
  3. controls/CMakeLists.txt：`QuickChartsControls` 同理
- 理由：ecm 降级（制品仓无 6.28.0）；SONAME（qt_add_qml_module 清版本属性 → 相对 NEEDED → 部署必挂）。
- 平台宏：无 `__OHOS__` 宏注入。

## 八、遗留问题与建议

1. **下游 find_package 消费**：`KF6QuickChartsConfig.cmake` 会 `find_dependency(ECM 6.26.0)` +
   `include(${ECM_MODULE_DIR}/ECMFindQmlModule.cmake)` + `ecm_find_qmlmodule(...)`。C++ 下游若用
   CMake 配置方式消费需自行具备 ecm（Conan 下 ecm 是 tool_require 不自动传递）。主要消费路径是 QML
   import（无需该配置），建议后续在 kquickcharts 的 package_info 里考虑声明 ecm 为
   tool_require 并让下游带齐。
2. **qmltypes 校验**：`qmldir` 里声明了 `QuickCharts.qmltypes`；测试已验证类型可实例化，
   未单独跑 `qmlimportscanner` 静态校验。
3. **CONAN_RUNTIME_LIB_DIRS**：recipe 已设（qtbase lib），供 RPATH 注入；OHOS 上 `$ORIGIN` 解析不稳定，
   以 LD_LIBRARY_PATH 运行为准。
