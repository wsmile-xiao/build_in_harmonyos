# kodi-platform

Kodi add-on 平台支持库，提供 Kodi PVR 插件使用的 XML 工具（XMLUtils）。

## 功能概述

- **XML 读写工具**：`XMLUtils::SetInt/SetString/SetFloat/SetHex/SetPath/SetBoolean` 写入
- **XML 读取工具**：`GetInt/GetString/GetFloat/GetHex/GetPath/GetBoolean` 及范围钳制变体
- **结构辅助**：`HasChild`、`GetEncoding`（文档编码声明）、`HasUTF8Declaration`
- PVR add-on 设置文件（settings.xml）读写的标准路径

## OHOS 适配

### 适配要点

1. **上游构建系统依赖 kodi-addon-dev SDK**：`find_package(Kodi REQUIRED)` 需要
   FindKodi.cmake / KodiConfig.cmake（ohpcd registry 无 kodi 包）。但源码
   （唯一 TU `src/util/XMLUtils.cpp`）不 include 任何 Kodi 头文件，实际链接
   依赖只有 tinyxml 与 p8-platform。配方自带 `recipe-cmake/CMakeLists.txt`
   （经 `build_script_folder` 消费）构建上游原样源码
2. **静态库编译**：libkodiplatform.a，无运行时依赖（tinyxml/p8-platform 静态并入）
3. **安装布局与上游一致**：`include/kodi/util/XMLUtils.h`，下游 add-on 的
   `#include <kodi/util/XMLUtils.h>` 无需改动

### 已知问题

- 无

### 与 Linux 的差异

- E092: CMake 无 HarmonyOS 平台模块，`CMAKE_SYSTEM_NAME=Linux` 绕过
- 其余 POSIX API 兼容，musl libc 无障碍

## 依赖关系

### 编译依赖

- CMake 3.15+
- C++17 编译器
- tinyxml/2.6.2（ohpcd registry）
- p8-platform/2.1.0（ohpcd registry）

### 运行依赖

- 无（静态库）

## 解锁下游

- kodi-pvr 系列 PVR 插件（XMLUtils 是其 settings 读写依赖）

## 参考资料

- 官方仓库：https://github.com/xbmc/kodi-platform
- 上游 tag：`kodiplatform-20250416`（注意前缀）
