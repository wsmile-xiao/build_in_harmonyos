# DRAFT: CMakeDeps 包级 config 遮蔽原生 Qt5Config + install(EXPORT) 烤入构建期 target 状态

## 现象

KF5/Qt5 链消费者（如 knotifications5 5.116.0，依赖 qt5-qtbase/5.15.2.2 +
kcoreaddons5 + kconfig5 + kwindowsystem5）在 conan create 的 test_package
阶段出现两类失败：

1. `Could not find a package configuration file provided by "Qt5DBus"
   (requested version 5.15.2)`——来自已安装包的
   `KF5NotificationsConfig.cmake:35 (find_dependency)`
2. `fatal error: 'QList' file not found`——消费端 flags.make 里没有任何
   Qt include 路径（尽管链接了 Qt5::Core）

## 根因（两个叠加）

### 1. CMakeDeps 包级 config 遮蔽原生 Qt5Config

qt5-qtbase 的 recipe 同时具有：
- 组件级 `cmake_file_name`（Qt5Core/Qt5Gui/...）
- 包内自装的原生 `lib/cmake/Qt5/Qt5Config.cmake`（完整 per-module config）

当消费端配方声明 `generators = "CMakeDeps"` 时，CMakeDeps 在 generators
目录生成包级 `Qt5Config.cmake`（由包名映射），且 conan_toolchain.cmake 把
generators 目录 PREPEND 到 CMAKE_PREFIX_PATH 最前——**遮蔽原生 config**。
CMakeDeps 版本的组件 include 变量
（`qt5-qtbase_Qt5_Core_INCLUDE_DIRS_RELEASE`）为空，消费端拿不到
`include/QtCore`。

### 2. install(EXPORT) 烤入构建期 target 状态

KDE 项目顶层 CMakeLists 常见模式：

```cmake
set(HAVE_DBUS FALSE)
if (TARGET Qt5::DBus)
    set(HAVE_DBUS TRUE)
endif()
```

构建期 CMakeDeps **定义了 Qt5::DBus 组件 target**（即使真实 Qt5DBus
库不存在——qt/5.15.19 构建 -no-dbus），于是 HAVE_DBUS=TRUE 被
`KF5NotificationsConfig.cmake.in` 的 `if (@HAVE_DBUS@)` 烤成
`if (TRUE) find_dependency(Qt5DBus 5.15.2)`，消费端无法解析
Qt5DBusConfig.cmake（CMakeDeps 不生成组件级 config 文件名）而 configure 失败。

## 修复

1. **消费端不用 CMakeDeps 处理 Qt5 线**：配方与 test_package 不声明
   `generators = "CMakeDeps"`；手写 `conan_cmakedeps_paths.cmake`，
   把 qt5-qtbase 包内原生 `lib/cmake` PREPEND 到 CMAKE_PREFIX_PATH
   （kconfig5 5.116.0 test_package 先例）。
2. **patch 构建期状态源**：顶层 CMakeLists 的 `if (TARGET Qt5::DBus)`
   强制 `if (FALSE)`（连同 src/tests 的同款守卫），使导出 config 的
   DBus 依赖条件为 FALSE，DBus-only 源码不进构建。
3. **无条件 `#else` 分支补宏守卫**：`#elif defined(QT_DBUS_LIB)` +
   降级实现（如 Popup 动作降级 NotifyByTaskbar）。
4. **CI 诊断侧（实锤补充，2026-10-02/03 knotifications5 #12316）**：
   - conandata.yml 只写官方原始 URL 单条（R39）——CI Pre-download 阶段
     会自动"还原为官方 URL"并处理镜像回退，手动加镜像列表对 CI 无效；
   - CI 报"源码下载超时"时先看日志尾：若为 `SSH bridge exec failed:
     connection refused`（elapsedTime 毫秒级、worker-prep 未执行）则是
     worker 基础设施病机假失败，纯 /rebuild 撞健康机即可（#12316 实测
     11 轮假失败后 CI-019 一次全绿），不要动 conandata。

## 关联

- E216（CMakeDeps 组件 INTERFACE_INCLUDE_DIRECTORIES 为空的另一场景）
- E537（无 SONAME 的 path-form DT_NEEDED）
- 实证：knotifications5 5.116.0（PR pending），本地 conan create
  package_id 6da5865a4a2cee3d8c4872f833a3c41e9d0a71e0 全绿
