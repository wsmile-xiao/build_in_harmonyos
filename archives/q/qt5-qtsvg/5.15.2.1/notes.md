# qt5-qtsvg 5.15.2.1 适配笔记

## 项目简介
Qt5 SVG 模块——Qt 5.15 的 SVG 渲染模块（libQt5Svg.so，提供 QSvgRenderer 等
SVG 解析/渲染 API）。LGPL-3.0。qmake 构建。

本配方为**生态补丁版本 5.15.2.1**：上游源码为 Qt 5.15.2 官方 tarball
（qtsvg-everywhere-src-5.15.2.tar.xz，sha256 8bc3c2c1），版本号 5.15.2.1
为 OpenHarmony 生态补丁版本（同 qt5-qtbase/5.15.2.2 模式）。

## 依赖与制品仓
- **qt5-qtbase/5.15.2**（制品仓已发布）——qmake/mkspecs/Core/Gui 依赖
- 无第三方 conan 依赖

## 构建与适配（同制品仓 5.15.2 先例）
1. **qmake 构建**：qtbase 的 qmake -spec linux-clang + make（QMAKE_STRIP="" 防 strip——OHOS loader 拒绝 stripped ELF）；
2. **_fix_qtbase_paths**：修 qtbase 包的 qt.conf 与 .pri（构建目录 → 包目录，HMDFS 路径）；
3. **CC/CXX 注入**：从 conf tools.build:compiler_executables 取 clang/clang++，PATH 加 qtbase/bin、QTDIR 指向 qtbase 包；
4. **package**：库/头/插件/mkspecs/cmake 配置复制 + 动态查找 .so 补符号链接（HMDFS 不保留 symlink）；
5. **package_info**：components Qt5Svg，libs=Qt5Svg，requires Qt5Core/Qt5Gui。

## 验证
- 模拟 CI 干净 PATH conan create（--build=missing, ohos-aarch64 profile）。

## 参考
- 制品仓 qt5-qtsvg/5.15.2（先例配方，本配方升级版）
- 制品仓 qt5-qtbase/5.15.2（生态补丁版本号模式参照）
