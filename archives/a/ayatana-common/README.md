# ayatana-common (libayatana-common)

Ayatana System Indicators 的公共库（上游名 libayatana-common），提供系统指示器
（ayatana-indicator-common 等）所需的共享工具：

- 桌面会话检测：`ayatana_common_utils_is_lomiri/is_unity/is_gnome/...`
- 程序查找：`ayatana_common_utils_have_program`
- 命令/URL 执行辅助：`execute_command`、`open_url`
- `org.ayatana.common` GSettings schema（`max-menu-text-length` 等）

## 功能概述

- 纯 C 实现，CMake 构建，产物为共享库 `libayatana-common.so`
- 头文件：`include/ayatana/common/utils.h`
- 提供 `libayatana-common.pc`（pkg-config）
- 安装 `org.ayatana.common.gschema.xml`（运行时被 `ellipsize` 读取）

## OHOS 适配

- 新增 `cmake/FindGSettings.cmake`，替代 Ubuntu `cmake-extras` 的 GSettings
  模块（OHOS 无该包），用于安装 gschema XML。
- `po/`（翻译）在缺少 `Intltool` CMake 模块时自动跳过（顶层 CMakeLists 守卫）。
- GObject-Introspection / Vala 绑定与翻译未构建（OHOS 无对应工具链）。
- 依赖 glib/2.84.0.1（提供模块化 .pc：glib-2.0/gio-2.0/gobject-2.0）。

## 依赖关系

- 编译依赖：glib-2.0 >= 2.36、gio-2.0 >= 2.36（Conan: glib/2.84.0.1）
- 运行依赖：glib、GSettings 后端（schema 需 glib-compile-schemas 编译）

## 参考资料

- 上游源码: https://github.com/AyatanaIndicators/libayatana-common
- 许可证: GPL-3.0-or-later
