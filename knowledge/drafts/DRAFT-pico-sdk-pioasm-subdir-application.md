# DRAFT-pico-sdk-pioasm-subdir-application：pico-sdk 只构建 tools/pioasm 子项目

> Contributor: pico-sdk 2.2.0 适配 | Status: Draft | Updated: 2026-08-25
> Source: archives/p/pico-sdk/2.2.0

## 现象

pico-sdk 的顶层 CMake 不是普通 host library 工程，而是 RP2040/RP2350 固件 SDK 入口。直接配置顶层工程容易卷入 board/platform、裸机工具链、固件测试以及外部 submodule。

## 根因

`tools/pioasm` 是 pico-sdk 中相对独立的 host-side CMake 子项目，源码内已带生成好的 lexer/parser。它能在 OHOS-native 上编译成 `bin/pioasm`，而顶层 SDK 的完整固件构建不适合作为三方库 OHOS 包装的 L1 smoke。

## 推荐做法

- `cmake.configure(build_script_folder=os.path.join(self.source_folder, "tools", "pioasm"))`
- 设置 `PIOASM_VERSION_STRING=<recipe version>`。
- 设置 `PIOASM_GENERATE_PARSER=OFF`，避免引入 Bison/Flex。
- 包装为 `application`，打包 `bin/pioasm` 和 `share/pico-sdk`。
- `test_package` 运行 `pioasm --version` 并把最小 `.pio` 程序生成 C SDK header。

## 验证证据

pico-sdk 2.2.0 在 OHOS shadow CI r4 通过：L0/L1/L2/L4/L5 全 pass，L2 为 `pioasm --version OK`，L5 为 `bin/ has content`。

## 禁止做法

不要在当前 PR 中强行补齐 tinyusb/cyw43/lwip/mbedtls/btstack 并跑顶层固件工程；这些是后续功能范围或依赖拆分问题。