# DRAFT-pico-sdk-empty-submodules-scope：pico-sdk 空 submodule 目录的范围裁剪

> Contributor: pico-sdk 2.2.0 适配 | Status: Draft | Updated: 2026-08-25
> Source: archives/p/pico-sdk/2.2.0

## 现象

pico-sdk 2.2.0 的 `.gitmodules` 声明了 `tinyusb`、`cyw43-driver`、`lwip`、`mbedtls`、`btstack`，但 Debian `orig.tar.gz` 中这些目录为空。

## 判断

`tools/pioasm` 不依赖这些 submodule，可以独立构建。当前包的功能范围是 `pioasm` host 工具和 SDK 源码路径，而不是完整 RP 系列固件生态。

## 推荐做法

- 在 notes/report 中明确当前范围：`pioasm + share/pico-sdk`。
- 打包时保留空目录占位，避免下游检查路径时报目录缺失。
- 不在当前 PR 中执行 `git submodule update` 或 vendoring 外部仓库。
- 后续如需 USB/Wi-Fi/network/Bluetooth SDK 能力，按依赖库单独适配、单独发布。

## 验证证据

pico-sdk 2.2.0 的 OHOS shadow CI r4 中，Conan graph 无依赖；`pioasm` 构建、安装、`test_package` smoke 均通过。