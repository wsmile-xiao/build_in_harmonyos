# layer-shell-qt 6.7.2 适配笔记

## 编译环境
- 构建系统: cmake (KDE ECM)
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 状态: published

## 编译步骤
```bash
# conan-verify（内含 conan create 全量构建）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify layer-shell-qt 6.7.2
# W3 本地 CI 模拟（嵌入 finish）
python3 $SKILL_ROOT/scripts/ohc-run.py finish layer-shell-qt 6.7.2 published
```

关键 configure 变量（conanfile.py generate()）：
- BUILD_SHARED_LIBS=ON, KF_IGNORE_PLATFORM_CHECK=TRUE, CMAKE_CXX_STANDARD=20
- ECM_MODULE_PATH 手动注入（CMakeDeps 不传播）
- WaylandScanner_EXECUTABLE 取 qtbase libexec
- QT_ADDITIONAL_PACKAGES_PREFIX_PATH 注入 qtwayland/qtdeclarative 等包路径
- conan_cmakedeps_paths.cmake 手动生成（qtbase cmake_find_mode=none）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 make 期 "No rule to make target //.../.cache/conan2/p/b/.../wayland-protocols/staging/xdg-activation/xdg-activation-v1.xml" | wayland-protocols 包内 .pc 硬编码构建机旧缓存路径 (.cache/conan2)，ECM FindWaylandProtocols 经 pkg-config 读到失效 pkgdatadir | generate() 重写 wayland-protocols.pc（prefix=真实 package_folder）并 PKG_CONFIG_PATH 前置注入；tc.cache_variables 兜底 |
| 2 | G2 编译期 "no struct named 'wl_fixes' in the global namespace"（qwayland-wayland.h） | Qt 6.11.1 私有头声明 wl_fixes 协议接口，wayland/1.22.0 协议头无此接口；且两者 include guard 同名 (WAYLAND_CLIENT_PROTOCOL_H)，layer-shell-qt 先 include <wayland-client.h> 导致 Qt 协议头被 guard 跳过 | patch 0002：qwaylandlayersurface_p.h 先 include <QtWaylandClient/private/wayland-wayland-client-protocol.h> 再 include <wayland-client.h> |
| 3 | test_package CMake "Target ... links to LayerShellQt::LayerShellQt but the target was not found" | 包安装导出 target 为 LayerShellQt::Interface（libLayerShellQtInterface.so），非 LayerShellQt::LayerShellQt | test_package CMakeLists 改链 LayerShellQt::Interface；cpp_info.libs 改为 LayerShellQtInterface |
| 4 | W3 JC5 扫到 main 上其他包 (cloog/kics) 遗留隐藏文件 | layer-shell-qt 未提交时 JC5 回退 full 模式整仓扫描 | 将 layer-shell-qt 配方提交到 feat/layer-shell-qt-6.7.2 分支，JC5 转 incremental 模式只看本次改动 |

## 源码修改
- patches/0001-xkbcommon-direct-link.patch: libxkbcommon pkg-config prefix 损坏，find_library 直接链接
- patches/0002-wayland-protocol-include-order.patch: include 顺序修复 wl_fixes 声明

## 依赖版本
qtwayland/6.11.1, qtdeclarative/6.11.1, wayland/1.22.0, wayland-protocols/1.36,
libxkbcommon/1.6.0, qtbase/6.11.1.2, ecm/6.26.0 (tool_require)

## 验证结果
- conan-verify G0-G4 + L2/L4/L5 全部 PASS
- W3 本地 CI: build_and_test.sh 1/1 100% pass
- ctest: test_layershellqt Passed 0.21s
- ELF 检查: SONAME 正确，DT_NEEDED 全为 basename，无绝对 conan 路径泄漏 (E537)

## 交付物
- libLayerShellQtInterface.so.6.7.2 (公共库，SONAME libLayerShellQtInterface.so.6)
- layer-shell.so (Qt Wayland shell integration 插件，SONAME liblayer-shell.so)
- LayerShellQtQml QML 模块 (org.kde.layershell)

## 注意事项
- 产物 CMake target 名是 LayerShellQt::Interface（上游 EXPORT_NAME Interface）
- 未尝试 wayland 升级到 1.24.0（会触发 qtbase/qtwayland 二进制重编译，违反 R36）
---

**编译结束**: 2026-09-24 01:39
**最终状态**: published
