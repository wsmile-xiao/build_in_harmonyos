# rtosc

Realtime safe OSC (Open Sound Control) packet serialization and dispatch library, influenced by liblo and libmapper.

## 功能概述

- OSC 1.0 规范的消息与 Bundle 构造、解析与校验（`rtosc_message`、`rtosc_bundle` 系列）
- 参数迭代器与类型查询（`rtosc_narguments`、`rtosc_type`、`rtosc_argument`）
- 路径模式匹配与分发（`rtosc_match`、`Ports::dispatch`）
- C++ 侧端口、默认值、自动化、MIDI 映射、撤销历史等运行时组件（`rtosc-cpp`）
- 版本查询（`rtosc_current_version`，0.3.1 对应 0.3.1）

## OHOS 适配

- 构建系统为 CMake；核心库无强制依赖，可选的 liblo、JACK、FLTK/NTK、Ruby、Doxygen 在 HarmonyOS 环境均不存在，保持默认关闭。
- 上游 `CMakeLists.txt` 要求 `cmake_minimum_required(VERSION 2.8)`，配方经 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容新版 CMake，不修改上游源码。
- 上游安装规则与 `GNUInstallDirs` 仅在 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 时启用；配方在 OHOS 下固定 `CMAKE_SYSTEM_NAME=Linux`（仓库内 rttr/zstr 同款做法），从而复用官方安装路径。
- 上游 ctest 共 28 项（C 15 项 + C++ 13 项），配方在 `build()` 内全量编译并执行，不跳过、不豁免。

## 依赖关系

- 编译依赖：无（纯 C/C++，仅需 C99 与 C++11）。
- 可选依赖（上游自动探测，OHOS 下均关闭）：liblo（`liblo-test`、`port-checker`、`performance` 扩展）、JACK、FLTK/NTK 示例、Ruby 端口检查、Doxygen 文档。

## 参考资料

- 上游仓库：https://github.com/fundamental/rtosc
- 版本标签：https://github.com/fundamental/rtosc/releases（v0.3.1）
- OSC 规范：https://opensoundcontrol.stanford.edu/spec-1_0.html
