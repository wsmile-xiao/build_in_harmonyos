# ableton-link

Ableton Link 是跨应用/设备同步音乐节拍（beat）、速度（tempo）与相位（phase）的技术，由 Ableton 开源。本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

https://github.com/Ableton/link

## 许可证

GPL-2.0-or-later

## 特性

- header-only 库（`Ableton::Link` 为 IMPORTED INTERFACE 目标，无编译产物）
- 公共 API 见 `include/ableton/Link.hpp`（`ableton::Link` / `BasicLink<Clock>`）
- 上游单元测试基于 Catch2：`LinkCoreTest`（16 用例）+ `LinkDiscoveryTest`（9 用例），共 25 个 TEST_CASE
- 依赖 asio-standalone（submodule，打包时随包 vendored 到 include/）

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 3.1.2 | built | 2026-08-11 | cmake | 3 |

## 已知平台问题

- CMake 不识别 HarmonyOS（E092），配方以 `CMAKE_SYSTEM_NAME=Linux` 构建
- examples（LinkHut）依赖 PortAudio，OHOS 不可用，已通过 `LINK_BUILD_EXAMPLES=OFF` 禁用
