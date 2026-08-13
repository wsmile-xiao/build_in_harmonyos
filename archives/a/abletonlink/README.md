# Ableton Link

Ableton Link 是一种在多个应用、多台设备之间实时同步音乐节拍（beat）、速度（tempo）与相位（phase）的技术。它基于 UDP 局域网组网，适合音乐制作、DJ 与现场演出场景。本归档适配的版本为 3.1.2。

## 功能概述

- **节拍/速度同步**：通过 SessionState 读写 tempo，并映射 beat 与时间轴
- **相位对齐**：beatAtTime / phaseAtTime / timeAtBeat 提供量子化对拍
- **局域网发现与组网**：基于 asio 与 UDP 的 peer 发现、心跳与网关
- **传输控制**：start/stop 同步（可选特性）

## OHOS 适配

- 库为 **header-only**（`Ableton::Link` 是 CMake INTERFACE target），无编译产物，包内直接提供头文件
- `AbletonLinkConfig.cmake` 通过补丁为 `OHOS|HarmonyOS` 定义 `LINK_PLATFORM_LINUX`，复用 Linux 平台层（`clock_gettime(CLOCK_MONOTONIC_RAW)`、`getifaddrs`、`pthread_setname_np`），均可在 HarmonyOS PC 上工作
- 官方 release tarball **不含** `modules/asio-standalone` 子模块（空目录），配方单独下载 asio 1.28.0 放到预期路径；包内随附 asio 头文件保证下游可直接编译
- 上游 `-Weverything -Werror` 在跨平台编译下易失败，已通过补丁移除 `-Werror`
- 上游测试为 Catch2 可执行文件（LinkCoreTest / LinkDiscoveryTest），未注册 ctest，由配方在 build 阶段直接运行并统计

## 依赖关系

- 编译/运行依赖：asio 1.28.0（standalone，随包提供）
- 系统依赖：无（pthread/atomic 由 OHOS libc 提供）

## 参考资料

- 官网：https://ableton.github.io/link/
- 源码仓库：https://github.com/Ableton/link
- 发布 tag：https://github.com/Ableton/link/releases/tag/Link-3.1.2
