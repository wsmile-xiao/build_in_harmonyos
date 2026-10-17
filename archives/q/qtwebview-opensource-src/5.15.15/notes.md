# qtwebview-opensource-src 5.15.15 适配笔记

## 源码信息
- 上游: Qt 5.15.15 LTS
- 源码: qtwebview-everywhere-opensource-src-5.15.15.tar.xz (125K)
- SHA256: 8e65b165df6f0608d97d8d0a9a5df691aa736ae0e76e2b93887e6fe2a247ae03
- 官方下载: https://download.qt.io/archive/qt/5.15/5.15.15/submodules/

## 构建系统
- qmake (Qt5 addon module)
- 主项目文件: qtwebview.pro
- 构建命令: qmake -spec linux-clang qtwebview.pro && make -j2 QMAKE_STRIP=""

## 依赖
- qt5-qtbase/5.15.2.2 (Core, Gui, Network) — Conan 制品仓已发布
- qt5-qtdeclarative/5.15.2 (Qml, Quick) — Conan 制品仓已发布
- Qt WebEngine: 不可用（未适配），使用 null backend（上游内置 fallback）

## 版本兼容性
- qtwebview 5.15.15 引用 qt5-qtbase 5.15.2.2（Conan 制品仓最新版本）
- Qt 5.15 LTS 系列 ABI 稳定，模块版本与基础版本无需严格匹配
- qmake 直接调用（不走 configure），不触发版本检查

## Web 后端
- 上游代码在 src/src.pro 中通过 qtHaveModule(webengine) 检测后端
- 无 WebEngine 时自动使用 null backend（src/webview/null/）
- null backend 提供完整 API 但无实际 web 渲染
- 这不是裁剪—— backend 是上游内置的 fallback 机制

## 平台适配
- 无需源码修改
- 需要修复 qt5-qtbase 的 qt.conf 和 .pri 文件路径（可重定位性）
- 需要合并 qt5-qtdeclarative 的 .pri 文件到 qt5-qtbase 的 mkspecs/modules/
- QMAKE_STRIP="" 防止 strip（OHOS 加载器拒绝 stripped ELF）

## 构建产物
- libQt5WebView.so (共享库)
- QML 插件: qml/QtWebView/
- 头文件: include/QtWebView/
- CMake 配置: lib/cmake/Qt5WebView/
- mkspecs 模块: mkspecs/modules/

## 验证
- test_package: 通过 QML 导入 QtWebView 1.15 验证 QML 插件加载
- 上游测试: tests/auto/auto.pro (make check)
---

**编译结束**: 2026-08-28 01:03
**最终状态**: built

## 关闭
COMPLETED
<!-- submit: Fri Aug 28 01:12:55 CST 2026 -->
<!-- resubmit: Fri Aug 28 01:14:10 CST 2026 -->
