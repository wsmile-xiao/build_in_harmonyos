# gsl-lite

gsl-lite 是 Microsoft Guidelines Support Library (GSL) 的轻量级、单头文件（header-only）实现，提供 `gsl::span`、`gsl::not_null`、`gsl::finally`、`gsl::index` 等类型与算法。兼容 C++98 至 C++20 及更早的 C 编译器，依赖极少。

## 功能概述

- **Header-only**：单头文件 `include/gsl-lite/gsl-lite.hpp`，无需编译二进制
- **轻量**：无外部运行时依赖，可嵌入嵌入式/受限平台
- **丰富类型**：`span`、`not_null`、`finally`、`narrow`、`index`、`make_span` 等
- **契约检查**：支持 off / on / audit 策略与 throws / terminates / handler 响应配置
- **多平台**：支持 Linux、macOS、Windows、FreeBSD、OHOS

## OHOS 适配

- **构建系统**：CMake（安装头文件 + CMake config），header-only 无需交叉编译
- **依赖链**：无
- **本目录版本**：0.43.0（官方标签 v0.43.0，commit ce82d30b）
- **状态**：bootstrap 骨架阶段，待 adapt 精调
