# kconfig5

KDE Frameworks 5 - KConfig 配置系统（KConfig XT）。

KConfig 是 KDE 使用的配置系统，提供对配置文件的持久化读写（INI 风格与
X-KConfig 格式），以及 KConfig XT 代码生成工具（`kconfig_compiler_kf5`）
自动从 `.kcfgc`/`.kcfg` 定义生成 C++ 配置类。

本目录为 KF5 系列（Qt5）适配，版本轨道与 KF6 的 `kconfig` 区分。

## 构建（CMake + Qt5）

- 构建系统：CMake / Ninja
- 运行时依赖：`qt5-qtbase/5.15.2.2`（含 Qt5Xml；5.15.2 不含 Xml，不满足 KConfig 的
  `find_package(Qt5 Xml)` 硬依赖）
- 构建依赖：`ecm/6.20.0`（ECM 提供 KDE 框架 CMake 与 `QT_MAJOR_VERSION` 注入）
- 平台选项：`KF_IGNORE_PLATFORM_CHECK=TRUE`、`KCONFIG_USE_DBUS=OFF`、`KCONFIG_USE_QML=OFF`

## 版本

| 版本 | 说明 |
|------|------|
| 5.116.0 | 首次适配（本版本轨道） |

## 平台适配要点（详见 5.116.0/manifest.yaml）

- OHOS CMake 平台模块未定义 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`，需手动设置为
  `-Wl,-soname,`，否则 KF5 `.so` 无 DT_SONAME，消费者的 `DT_NEEDED` 记录相对路径
  导致运行时无法解析（E537）。
- `ECM_MODULE_PATH` 需手动从 ecm 包注入（CMakeDeps 不传播）。
- `ecm_install_po_files_as_qm(poqm)` 依赖 Qt5LinguistTools（qt5-qtbase 未含），配方以
  补丁禁用（与 KF6 kconfig 一致）。
- 命令行工具：`kreadconfig5`、`kwriteconfig5`（见 commands.json）。

## 归档规范

- `5.116.0/`：版本配方（conanfile.py、conandata.yml、test_package/、patches/）
- `commands.json`：命令行工具声明（R38）
