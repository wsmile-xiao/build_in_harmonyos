# Extra CMake Modules (ECM)

ECM 是 KDE 提供的额外 CMake 模块集合，为 CMake 构建系统提供额外功能。它包含了许多用于查找常见软件、执行常见任务以及配置项目的 CMake 模块。

## 功能概述

- **CMake 模块**: 提供 Find*.cmake 和其他辅助模块
- **构建工具**: 提供 KDE 风格的 CMake 配置和构建工具
- **打包支持**: 提供 CPack 和打包相关的模块
- **测试支持**: 提供测试框架集成模块

## OHOS 适配

- ECM 是纯 CMake 模块库，不编译任何二进制代码
- 仅安装 CMake 模块文件到 `share/cmake/ECM` 目录
- 无需补丁即可在 HarmonyOS 上安装
- 无额外依赖，只需要 CMake

## 依赖关系

- **编译依赖**: CMake (3.16+)
- **运行依赖**: 无（纯配置文件）

## 参考资料

- 官网: https://kde.org/products/frameworks/
- 源码仓库: https://invent.kde.org/frameworks/extra-cmake-modules
- 下载地址: https://download.kde.org/stable/frameworks/