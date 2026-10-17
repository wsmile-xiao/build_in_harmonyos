# plasma-wayland-protocols

> Plasma 使用的非标准 Wayland 协议 XML 描述（data-only 包）

## 简介

`plasma-wayland-protocols` 提供 Plasma 生态使用的非标准 Wayland 协议 XML 定义，
安装到 `<prefix>/share/plasma-wayland-protocols`，并附带一个 CMake 包配置
（`PlasmaWaylandProtocolsConfig.cmake`），后者定义下游使用的变量
`PLASMA_WAYLAND_PROTOCOLS_DIR`。

它是 **data-only** 包：不编译、不链接任何代码。

## 鸿蒙适配说明

- **构建系统**：CMake（无 C/C++ 编译产物）
- **平台**：OHOS / armv8（aarch64）
- **依赖**：无运行时依赖；构建期 `tool_requires` `ecm/6.26.0`
- **适配版本**：1.14.0
- **上游源**：https://download.kde.org/Attic/plasma-wayland-protocols/plasma-wayland-protocols-1.14.0.tar.xz
  （conandata.yml 中镜像优先、官方源同在列表中；四条 URL sha256 一致）
- **SHA256**：1a4385ecfc79f7589f07381cab11c3ff51f6e2fa4b73b78600d6ad096394bf81

## 下游引用

kwayland5/5.116.0 需要它：

```cmake
find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED)
# 之后使用 ${PLASMA_WAYLAND_PROTOCOLS_DIR}/<protocol>.xml
```

```python
# Conan 2.x
self.requires("plasma-wayland-protocols/1.14.0")
self.tool_requires("ecm/6.26.0")   # ECM 是构建期工具依赖
```

## 安装内容

- 30 个协议 XML + 2 个向后兼容重命名
  （`org-kde-plasma-virtual-desktop.xml` → `plasma-virtual-desktop.xml`、
  `zkde-screencast-unstable-v1.xml` → `screencast.xml`），
  合计 32 个 XML 安装到 `share/plasma-wayland-protocols/`
- `lib/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfig.cmake` +
  `PlasmaWaylandProtocolsConfigVersion.cmake`

## 已知平台限制

- 无（纯数据包；上游无测试套件，测试全部由 test_package 提供）
