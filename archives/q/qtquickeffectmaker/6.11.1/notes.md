# qtquickeffectmaker 6.11.1 适配笔记

## 上游信息
- 上游仓库: https://code.qt.io/cgit/qt/qtquickeffectmaker.git（Qt 官方模块）
- 版本: 6.11.1（官方 tarball，download.qt.io / TUNA 镜像）
- 功能: Qt Quick Effect Maker（QQEM），QML 着色器特效编辑器

## 编译环境
- 构建系统: CMake（qt_build_repo，Qt 内部模块构建）
- 编译器: clang 15（hnp 工具链，aarch64-linux-ohos）
- 状态: 成功

## 编译要点
- 依赖 qtbase/6.11.1（Qt6BuildInternals 提供 qt_internal_* 构建宏）、
  qtdeclarative/6.11.1（Qt::Quick/Qml）、qtshadertools/6.11.1（Qt::ShaderTools）；
  qtquick3d 为可选（Quick3DGlslParserPrivate 仅语法高亮）
- 上游 CMakeLists 在 `CMAKE_CROSSCOMPILING` 时直接跳过构建：
  通过 toolchain block 把系统呈现为 Linux 并置 CMAKE_CROSSCOMPILING=FALSE
  （同 qtdeclarative 6.11.1 配方模式）
- CMAKE_PREFIX_PATH 指向 qtbase 包，QT_ADDITIONAL_PACKAGES_PREFIX_PATH
  指向 qtdeclarative/qtshadertools 包

## 运行验证
- test_package: 链接 Qt6::QuickEffectMaker（QQuickEffect 头）+ 验证
  QtQuickEffectMaker QML 模块可加载（offscreen 平台）
