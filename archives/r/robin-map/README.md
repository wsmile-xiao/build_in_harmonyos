# robin-map

C++ implementation of a fast hash map and hash set using Robin Hood hashing (header-only, C++17).

## 功能概述

- `tsl::robin_map` / `tsl::robin_set` 等容器
- 纯头文件 INTERFACE 库，无运行时链接库
- 通过 CMake 安装 `tsl-robin-map` 包配置，供下游 `find_package` 使用

## OHOS 适配

- 构建系统：CMake（安装头文件 + Config.cmake，无需编译二进制）
- CMake 包名：`tsl-robin-map`；目标：`tsl::robin_map`（与 Homebrew / nanobind 一致）
- 无外部库依赖；`settings.os` 兼容 `Linux` 与 `OHOS`（R32）
- 本包是 `nanobind`（Homebrew 方式，`NB_USE_SUBMODULE_DEPS=OFF`）的前置依赖（R36）

## 依赖关系

- 编译/安装：cmake
- 运行时：无

## 验证结果

- OpenHarmony 6.1 aarch64 Conan 构建与安装通过
- 上游 Boost.Test：132/132 通过
- Conan 消费测试：1/1 通过
- `conan-verify`：G0-G4、L2/L4/L5 全部通过

## 参考资料

- 上游：https://github.com/Tessil/robin-map
- Homebrew：https://formulae.brew.sh/formula/robin-map
