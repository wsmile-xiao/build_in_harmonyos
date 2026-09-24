# qtgraphs 6.8.2 OpenHarmony PC 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 适配范围

本包适配 Qt Graphs 6.8.2 官方子模块到 OpenHarmony PC（aarch64），构建上游 CMake 工程并打包 Qt Graphs 库、QML 插件元数据与 CMake 包文件。

## 跨版本构建策略（核心决策）

制品仓（ohpcd remote）中**没有 Qt 6.8.2 系列包**（qtbase/qtdeclarative/qtshadertools 均只有 6.11.1），而 Qt 子模块构建要求 qtbase 与模块版本严格同版（版本同步检查）。本适配沿用仓库已合入的跨版本先例：

- `qtremoteobjects/6.8.2`（已合入发布）：requires qtbase/6.11.1，notes 明确"qtbase/6.8.2 is NOT available in the ohpcd Conan remote"
- `qtserialport/6.8.2`（已合入发布）：同样 requires qtbase/6.11.1，notes 记录"CMake find_package(Qt6 6.8.2 ...) 接受 Qt6 6.11.1（版本兼容：6.11.1 >= 6.8.2）"

实测验证：qtgraphs 6.8.2 源码对 qtbase 6.11.1（含 BuildInternals 构建系统）+ qtdeclarative 6.11.1（含 QuickShapesPrivate 私有 API）交叉构建，configure/build/上游测试全部通过，无版本同步错误、无私有 API 兼容问题。生成的 `Qt6GraphsConfigVersionImpl.cmake` 声明 `PACKAGE_VERSION "6.8.2"`（取自 PROJECT_VERSION），`qtgraphsversion.h` 中 `QTGRAPHS_VERSION_STR` 取自所装 Qt 栈（"6.11.1"），属跨版本构建的正常现象，与 qtremoteobjects/qtserialport 6.8.2 一致。

qtshadertools/6.11.1 保留在 requirements 中的原因：qtdeclarative 包的 `qtdeclarative::qml` component 在 package_info 中声明了 `qtshadertools::shadertools` 依赖，conan 依赖图要求其存在。

## 3D 功能与 qtquick3d 缺失

- qtgraphs 6.8.2 的 `src/configure.cmake` 中 `graphs-3d` 特性以 `CONDITION TARGET Qt6::Quick3D` 门控
- 制品仓无 qtquick3d（任何版本），与 qtgraphs/6.11.1、qt6-quick3dphysics 6.8.2 适配时的情况一致
- 配方显式传 `FEATURE_graphs_3d=OFF`（与 6.11.1 配方一致），即使环境中日后出现 Qt6Quick3D 也保持排除显式化
- 3D 上游测试套件（cpptest 23 个 + qmltest 1 个 CTest 目标）因此被门控排除，在 PR 正文中如实申报

## 编译步骤

上游 CMake 配置（由配方 generate() 注入）：

```text
CMAKE_PREFIX_PATH=<qtbase 6.11.1 conan 包目录>
CMAKE_MODULE_PATH=<qtbase>/lib/cmake/Qt6/platforms
Qt6_DIR/Qt6Qml_DIR/Qt6Quick_DIR/Qt6ShaderTools_DIR=<各 conan 包 cmake 目录>
QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qtdeclarative>;<qtshadertools>
QT_QMAKE_TARGET_MKSPEC=harmonyos-clang
BUILD_SHARED_LIBS=ON
BUILD_TESTING=ON / QT_BUILD_TESTS=ON / QT_BUILD_TESTS_BY_DEFAULT=ON
QT_BUILD_EXAMPLES=OFF
FEATURE_graphs_3d=OFF
```

无源码补丁。6.11.1 适配中两处源码调整在 6.8.2 均不需要：
- 6.8.2 的 `tst_datetimeaxis.cpp` 本身使用 `QTimeZone::UTC`（6.11.1 的 Europe/Helsinki 时区数据问题不存在）
- 2D 构建无需向上游 `find_package(... OPTIONAL_COMPONENTS ...)` 追加 ShaderTools（2D 着色器为源码树自带预编译 .qsb，构建期无 qsb 编译需求；实测 configure/build 全绿）

## 上游测试（R51 三步法）

### 清点（tests/auto 共 41 个 CTest 目标）

| 套件 | 目标数 | 状态 |
|------|--------|------|
| cpp2dtest | 16 | 启用（qgtheme-graph/qgtheme-series 两目录上游 CMake 未接线，不计入） |
| qml2dtest | 1 (tst_qgqml2dtest) | 启用 |
| cpptest | 23 | 阻塞（3D，需 Qt6Quick3D） |
| qmltest | 1 (tst_qgqmltest) | 阻塞（3D，需 Qt6Quick3D） |
| tests/manual | 27 目录 | 交互式显示环境手动测试，不计入 auto 目标 |
| tests/baseline | - | 6.8.2 无此目录 |

### 实测运行（本机 OHOS aarch64，2026-09-23）

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --output-on-failure --timeout 300
# 17/17 通过（16 cpp2dtest + 1 qml2dtest），0 失败
# qml2dtest 需 QML2_IMPORT_PATH 含构建目录 qml/（配方 _run_qml_dirs 已处理）
```

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| qtbase | 6.11.1 | 已发布（跨版本：6.8.2 未发布） |
| qtdeclarative | 6.11.1 | 已发布（跨版本：6.8.2 未发布） |
| qtshadertools | 6.11.1 | 已发布（跨版本：6.8.2 未发布） |

## 验证结果

- conan create（W3 本地验证）：通过，上游 17/17 CTest 目标全绿
- test_package 消费者冒烟：链接 Qt6::Graphs，验证 2D Bar/Line/Scatter 系列 API 与版本宏

## R40 手动验证标记

Headless CI 仅覆盖构建/链接/非渲染冒烟。Qt Graphs 渲染、QML 集成、EGL/GLES scene graph 行为需 OpenHarmony PC 显示会话人工验证；完成前状态保持 built，不得仅凭 CI 冒烟升级为 published。
---

**编译结束**: 2026-09-23 13:51
**最终状态**: built
