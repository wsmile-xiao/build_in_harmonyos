# arduinojson 7.4.2 for HarmonyOS

## 概述

ArduinoJson 是用于 Arduino 与 IoT 场景的 C++ JSON 库（header-only）。本归档记录其在
HarmonyOS/OpenHarmony PC（aarch64）上的适配结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | arduinojson |
| 版本 | 7.4.2 |
| 下载地址 | https://github.com/bblanchon/ArduinoJson/archive/refs/tags/v7.4.2.tar.gz |
| 官方文档 | https://arduinojson.org |
| 许可 | MIT |

## 适配说明

- 纯 header-only（CMake INTERFACE 目标），无编译产物，仅安装头文件到 include/。
- Conan 配方使用 CMakeToolchain；`BUILD_TESTING=OFF` 避免 conan create 触发
  extras/fuzzing（OHOS libclang_rt.fuzzer.a 与 libc++ 符号不匹配，详见 notes.md）。
- 上游测试位于 extras/tests（Catch 框架），本机 ctest -E fuzzer 27/27 通过。
- test_package 使用 C++ 消费者测试（.cpp 源），真实调用
  serializeJson/deserializeJson/JsonVariant/containsKey/版本宏。

## 版本历史

- 7.4.2：首次适配。
