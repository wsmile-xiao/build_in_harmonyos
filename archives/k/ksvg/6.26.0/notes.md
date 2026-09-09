# ksvg 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (OHOS SDK 15)
- 状态: built

## 软件简介

KSvg 是 KDE Frameworks 6 Tier 3 库，用于渲染基于 SVG 的主题（Plasma
主题系统的基础库），支持 stylesheet 重新着色与磁盘缓存。产物两个：

1. `libKF6Svg.so` — 核心库（KSvg::Svg / KSvg::FrameSvg / KSvg::ImageSet），
   QImage/QPainter 软件渲染路径
2. `org.kde.ksvg` QML 插件 — declarativeimports（SvgItem / FrameSvgItem，
   Qt Quick 场景用）

## 与前人失败记录的关系

main 上 `archives/k/ksvg/6.26.0/` 只有前人失败的 reports/（G4 Archive
FAIL：无配方、manifest 缺 build_system、无二进制）。本次是全新适配，
不背它的锅；其 test-report 提示的"测试需 GUI 运行时"问题已通过
QT_QPA_PLATFORM=offscreen + QImage 软渲染路径解决（本机是 arm64 OHOS，
能直接跑 Qt 测试二进制）。

## 编译步骤

conan create（模式 A），关键 CMake 配置：
- `-DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON`
- `-DKF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）
- `-DKF_SKIP_PO_PROCESSING=ON`（无 Qt6LinguistTools）
- `-DBUILD_TOOLS=OFF`（上游默认，split-plasma-svgs 不构建）
- `-DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_QMLDIR=lib/qml`
- SONAME 注入（Generic 平台模块无 soname 规则，E330）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(KF6 6.26.0) 失败 | ohpcd 发布的 KF6 组件版本上限：karchive 6.19.0、kcolorscheme/kguiaddons/kirigami 6.18.0 | 补丁 0001 把 KF_DEP_VERSION 降到 6.18.0 |
| 2 | kconfig 版本冲突（kcolorscheme/6.18.0 锁 kconfig/6.18.0，与 kconfig/6.26.0 冲突） | kcolorscheme 6.18.0 导出的 Config 里 find_dependency(KF6Config "6.18.0") | 全链统一用 6.18.0（kconfig/kcoreaddons 6.18.0） |
| 3 | ECMQmlModule 把缺 Qt6Qml 升级为 REQUIRED（knotifications #8662 的坑） | 早期以为 qtbase 裁剪包无 Qml | **qtdeclarative/6.11.1 已发布**（含 Qt6Qml/Qt6Quick/Qt6QuickControls2 完整组件+二进制），ksvg 全量构建含 QML 插件，无需禁用 |
| 4 | QML 模块构建要 qmlcachegen/qmlimportscanner 等宿主工具 | ecm_add_qml_module 调用 qtdeclarative 包内工具（arm64 OHOS ELF） | PATH prepend qtdeclarative 的 bin/ 与 libexec/（kirigami 6.18.0 先例） |
| 5 | libKF6Svg.so 无 DT_SONAME | OHOS 原生构建 CMake 落 Generic 平台模块，无 soname 规则 | CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG 注入 -Wl,-soname,（kcodecs 76da86d28c 先例，E330） |
| 6 | 沙箱 libc++_shared.so 遮蔽 | /data/storage/el1/bundle/libs/arm64 下不兼容版本 | LD_LIBRARY_PATH 前置 /system/lib64（kconfig 6.26.0 先例） |
| 7 | karchive 6.19.0 导出的 find_dependency(ZLIB)/pkg_check_modules(LibZstd) | 发布包带 OPENSSL=TRUE/ZLIB 链 | 图中加入 zlib/1.3.1.1 + zstd/1.5.7，并暴露 zstd 的 pkgconfig 目录（kpackage 6.26.0 先例） |
| 8 | SVG 渲染测试需图形环境 | 前人 test-report 记录测试因缺 GUI 运行时失败 | QT_QPA_PLATFORM=offscreen + 测试用 QImage 软渲染路径（无需 X11/ Wayland）；本机为 arm64 OHOS 可直接执行测试二进制 |

## 源码修改

- patches/0001-lower-kf-dep-version.patch：KF_DEP_VERSION 6.26.0 → 6.18.0
- patches/0002-ohos-framecontrast-backport.patch：KColorScheme::frameContrast()
  是 kcolorscheme 6.26 API，在 imageset_p.cpp 按上游实现本地回移
  （ksvgFrameContrast()，读 KDE 配置组 frameContrast，默认 0.2）
- patches/0003-ohos-qml-kirigami-6.18-compat.patch：declarativeimports 的
  svgitem/framesvgitem 改用 kirigami 6.18 已有的 CONSTANT 属性
  m_kirigamiTheme->frameContrast()；删除 kirigami 6.18 不存在的
  frameContrastChanged 信号 connect（colorsChanged 仍刷新主题色）

## 依赖版本

- qtbase/6.11.1（Qt6::Gui）
- qtdeclarative/6.11.1（Qt6::Qml/Quick/QuickControls2，QML 插件构建用）
- qtsvg/6.11.1（Qt6::Svg 渲染后端）
- kconfig/6.18.0（KF6::ConfigCore/ConfigGui）
- kcoreaddons/6.18.0（KF6::CoreAddons）
- karchive/6.19.0（KF6::Archive，ohpcd cap）
- kcolorscheme/6.18.0（KF6::ColorScheme，ohpcd cap）
- kguiaddons/6.18.0（KF6::GuiAddons，KImageCache，ohpcd cap）
- kirigami/6.18.0（KF6::KirigamiPlatform，declarativeimports 用，ohpcd cap）
- zlib/1.3.1.1 + zstd/1.5.7（karchive 导出配置的传递依赖发现）
- ecm/6.26.0（tool_requires）

## 验证结果

```
conan create . -pr ci/conan/profiles/ohos-aarch64 --build=missing
# 上游 CTest：plasmasvg-svgtest / plasmasvg-framesvgtest / plasmasvg-imagesettest（3 个，offscreen 软渲染）
# test_package：test_ksvg 消费端 14 断言
```

## 注意事项

- kcolorscheme/kguiaddons/kirigami 发布新版本（6.26+）后，可考虑把
  KF_DEP_VERSION 升回 6.26.0 并同步升级依赖链
- QML 插件装到 lib/qml/org/kde/ksvg，消费方需设置 QML2_IMPORT_PATH
---

**编译结束**: 2026-09-07 00:38
**最终状态**: published
